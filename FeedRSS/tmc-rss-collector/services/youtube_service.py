"""
YouTube Service - Fetches video metadata and captions from YouTube.

Uses youtube-transcript-api for caption retrieval.
No API key required. No audio processing.
"""

import asyncio
import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# ========================================
# Custom Exceptions
# ========================================

class VideoNotFoundError(Exception):
    """Video does not exist or is private."""
    pass


class CaptionsNotAvailableError(Exception):
    """Video exists but has no captions in supported languages."""
    pass


class TranscriptionServiceError(Exception):
    """Generic service error."""
    pass


# ========================================
# YouTubeService
# ========================================

# Regex for extracting video ID from YouTube URLs
_VIDEO_ID_RE = re.compile(
    r'(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})'
)

# Default language priority
DEFAULT_LANGUAGES = ["pt", "pt-BR", "en", "es"]

# Maximum segments to return (cap for very long videos)
MAX_SEGMENTS = 200


def _normalize_transcript(raw) -> list[dict]:
    """
    Normalize transcript data from youtube_transcript_api into a list of dicts.

    Handles both dict-based (older versions) and attribute-based (newer versions)
    return types from the library, ensuring a consistent list[dict] output.
    """
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(item)
        else:
            # Handle FetchedTranscriptSnippet or similar objects with attributes
            result.append({
                "text": getattr(item, "text", ""),
                "start": getattr(item, "start", 0.0),
                "duration": getattr(item, "duration", 0.0),
            })
    return result


def _format_time(seconds: float) -> str:
    """
    Format seconds into MM:SS or HH:MM:SS string.

    Args:
        seconds: Time in seconds (float).

    Returns:
        Formatted time string.
    """
    total_secs = int(seconds)
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class YouTubeService:
    """Service for fetching YouTube video metadata and captions."""

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract 11-character video ID from a YouTube URL.

        Supports:
        - https://www.youtube.com/watch?v=XXXXXXXXXXX
        - https://youtu.be/XXXXXXXXXXX
        - https://www.youtube.com/embed/XXXXXXXXXXX
        - https://www.youtube.com/shorts/XXXXXXXXXXX

        Args:
            url: YouTube video URL.

        Returns:
            11-char video ID or None if invalid.
        """
        match = _VIDEO_ID_RE.search(url)
        return match.group(1) if match else None

    @staticmethod
    async def get_video_metadata(video_id: str) -> dict:
        """
        Fetch video metadata from YouTube oembed endpoint.

        Args:
            video_id: 11-character YouTube video ID.

        Returns:
            Dict with videoId, url, title, channel, thumbnail.

        Raises:
            VideoNotFoundError: If video does not exist or is private.
            TranscriptionServiceError: On unexpected HTTP errors.
        """
        oembed_url = (
            f"https://www.youtube.com/oembed"
            f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
        )
        original_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(oembed_url)

            if response.status_code in (400, 401, 404):
                raise VideoNotFoundError("Vídeo não encontrado ou é privado.")

            if response.status_code != 200:
                logger.error(
                    f"YouTube oembed retornou status {response.status_code} "
                    f"para video_id={video_id}"
                )
                raise TranscriptionServiceError(
                    "Erro ao buscar metadados do vídeo no YouTube."
                )

            oembed = response.json()

            return {
                "videoId": video_id,
                "url": original_url,
                "title": oembed.get("title", ""),
                "channel": oembed.get("author_name", ""),
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            }

        except VideoNotFoundError:
            raise
        except TranscriptionServiceError:
            raise
        except Exception as e:
            logger.exception(f"Erro inesperado ao buscar metadados do vídeo {video_id}: {e}")
            raise TranscriptionServiceError(
                "Erro ao buscar metadados do vídeo no YouTube."
            )

    @staticmethod
    async def get_captions(
        video_id: str,
        languages: Optional[list[str]] = None,
        target_duration: float = 45.0,
    ) -> dict:
        """
        Fetch and merge captions for a YouTube video.

        Args:
            video_id: 11-character YouTube video ID.
            languages: Language priority list. Defaults to ["pt", "pt-BR", "en", "es"].
            target_duration: Target duration per merged segment in seconds.

        Returns:
            Dict with:
                - segments: list of merged segment dicts
                - language: detected caption language
                - caption_type: "manual" or "auto-generated"
                - total_duration_seconds: total video duration

        Raises:
            CaptionsNotAvailableError: If no captions are available.
            VideoNotFoundError: If video is unavailable.
            TranscriptionServiceError: On unexpected errors.
        """
        if languages is None:
            languages = DEFAULT_LANGUAGES

        def _fetch_transcript():
            """Synchronous call to youtube_transcript_api v1.x (runs in thread)."""
            from youtube_transcript_api import YouTubeTranscriptApi

            api = YouTubeTranscriptApi()

            # First, try direct fetch with language priority (simplest path)
            # This handles both manual and auto-generated captions
            try:
                result = api.fetch(video_id, languages=languages)
                raw = result.to_raw_data()
                detected_language = result.language_code
                caption_type = "auto-generated" if result.is_generated else "manual"
                return raw, detected_language, caption_type
            except Exception:
                pass

            # Fallback: list available transcripts and pick best match
            transcript_list = api.list(video_id)

            # Try manual transcripts first, then auto-generated
            for find_fn, c_type in [
                (transcript_list.find_manually_created_transcript, "manual"),
                (transcript_list.find_generated_transcript, "auto-generated"),
            ]:
                for lang in languages:
                    try:
                        transcript = find_fn([lang])
                        result = transcript.fetch()
                        raw = result.to_raw_data()
                        return raw, lang, c_type
                    except Exception:
                        pass

            # Nothing found
            raise Exception("NoTranscriptFound")

        try:
            raw_segments, language, caption_type = await asyncio.to_thread(_fetch_transcript)
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            if "TranscriptsDisabled" in error_type:
                raise CaptionsNotAvailableError(
                    "Este vídeo não possui legendas disponíveis."
                )
            elif "NoTranscriptFound" in error_type:
                raise CaptionsNotAvailableError(
                    "Não foram encontradas legendas nos idiomas suportados (pt, en, es)."
                )
            elif "VideoUnavailable" in error_type:
                raise VideoNotFoundError(
                    "Vídeo não encontrado ou é privado."
                )
            elif "CouldNotRetrieveTranscript" in error_type:
                # This can happen for disabled subtitles or other issues
                if "disabled" in error_msg.lower() or "subtitles" in error_msg.lower():
                    raise CaptionsNotAvailableError(
                        "Este vídeo não possui legendas disponíveis."
                    )
                raise CaptionsNotAvailableError(
                    "Não foi possível obter as legendas deste vídeo."
                )
            else:
                logger.exception(f"Erro ao buscar legendas do vídeo {video_id}: {e}")
                raise TranscriptionServiceError(
                    "Erro ao buscar legendas do YouTube."
                )

        if not raw_segments:
            raise CaptionsNotAvailableError(
                "Este vídeo não possui legendas disponíveis."
            )

        # Calculate total duration from last segment
        last = raw_segments[-1]
        total_duration = last.get("start", 0) + last.get("duration", 0)

        # Merge segments
        merged = YouTubeService._merge_segments(raw_segments, target_duration)

        return {
            "segments": merged,
            "language": language,
            "caption_type": caption_type,
            "total_duration_seconds": int(total_duration),
        }

    @staticmethod
    def _merge_segments(
        raw_segments: list[dict],
        target_duration: float = 45.0,
    ) -> list[dict]:
        """
        Merge YouTube's fine-grained caption fragments (~2-5s each)
        into meaningful segments of ~30-60 seconds.

        Returns segments in the format CriarContext expects:
        {
            "id": "1",
            "startTime": "00:00",
            "endTime": "00:45",
            "text": "Merged text content...",
            "topic": ""
        }

        Merge algorithm:
        1. Accumulate fragments into a buffer.
        2. When accumulated duration >= target_duration AND the next fragment
           starts a new sentence (capital letter or period in previous),
           flush the buffer as a segment.
        3. Final buffer always flushed as last segment.
        4. Format startTime/endTime as "MM:SS" or "HH:MM:SS" if >= 1 hour.
        5. topic field left as empty string.

        Args:
            raw_segments: List of dicts with text, start, duration keys.
            target_duration: Target duration per merged segment in seconds.

        Returns:
            List of merged segment dicts, capped at MAX_SEGMENTS.
        """
        if not raw_segments:
            return []

        merged = []
        segment_id = 1

        buffer_texts = []
        buffer_start = raw_segments[0].get("start", 0.0)
        buffer_duration = 0.0

        for i, fragment in enumerate(raw_segments):
            text = fragment.get("text", "").strip()
            start = fragment.get("start", 0.0)
            duration = fragment.get("duration", 0.0)

            if not text:
                continue

            buffer_texts.append(text)
            buffer_duration = (start + duration) - buffer_start

            # Check if we should flush
            should_flush = False
            if buffer_duration >= target_duration:
                # Look for sentence boundary: current text ends with punctuation
                # or next fragment starts with uppercase
                if text.endswith(('.', '!', '?', '...', '。')):
                    should_flush = True
                elif i + 1 < len(raw_segments):
                    next_text = raw_segments[i + 1].get("text", "").strip()
                    if next_text and next_text[0].isupper():
                        should_flush = True
                    elif buffer_duration >= target_duration * 1.5:
                        # Force flush if we're 1.5x over target
                        should_flush = True
                else:
                    # Last fragment
                    should_flush = True

            if should_flush and buffer_texts:
                end_time = start + duration
                merged.append({
                    "id": str(segment_id),
                    "startTime": _format_time(buffer_start),
                    "endTime": _format_time(end_time),
                    "text": " ".join(buffer_texts),
                    "topic": "",
                })
                segment_id += 1
                buffer_texts = []
                buffer_start = end_time
                buffer_duration = 0.0

                # Cap at MAX_SEGMENTS
                if len(merged) >= MAX_SEGMENTS:
                    logger.warning(
                        f"Transcrição truncada em {MAX_SEGMENTS} segmentos"
                    )
                    break

        # Flush remaining buffer
        if buffer_texts and len(merged) < MAX_SEGMENTS:
            last_frag = raw_segments[-1]
            end_time = last_frag.get("start", 0.0) + last_frag.get("duration", 0.0)
            merged.append({
                "id": str(segment_id),
                "startTime": _format_time(buffer_start),
                "endTime": _format_time(end_time),
                "text": " ".join(buffer_texts),
                "topic": "",
            })

        return merged
