"""
YouTube Service - Fetches video metadata and captions from YouTube.

Caption retrieval strategy (tried in order):
1. InnerTube Player API via googleapis.com (no proxy, no API key needed)
2. youtube-transcript-api library (with proxy if configured)
3. Timedtext endpoint fallback (bare HTTP, last resort)

No audio processing.
"""

import asyncio
import logging
import os
import re
import xml.etree.ElementTree as ET
from html import unescape
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Proxy configuration (loaded once at module level)
_YOUTUBE_PROXY_URL = os.environ.get("YOUTUBE_PROXY_URL", "")
_WEBSHARE_PROXY_USER = os.environ.get("WEBSHARE_PROXY_USER", "")
_WEBSHARE_PROXY_PASS = os.environ.get("WEBSHARE_PROXY_PASS", "")
_YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# InnerTube client configs — tried in order for caption extraction
_INNERTUBE_CLIENTS = [
    {
        "name": "WEB",
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20250310.01.00",
            }
        },
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "api_key": "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
    },
    {
        "name": "ANDROID",
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "20.10.38",
            }
        },
        "user_agent": "com.google.android.youtube/20.10.38 (Linux; U; Android 14) gzip",
        "api_key": "AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w",
    },
    {
        "name": "IOS",
        "context": {
            "client": {
                "clientName": "IOS",
                "clientVersion": "20.10.3",
            }
        },
        "user_agent": "com.google.ios.youtube/20.10.3 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)",
        "api_key": "AIzaSyB-63vPrdThhKuerbB2N_l7Kwwcxj6yUAc",
    },
    {
        "name": "TVHTML5_EMBEDDED",
        "context": {
            "client": {
                "clientName": "TVHTML5_SIMPLY_EMBEDDED_PLAYER",
                "clientVersion": "2.0",
            },
            "thirdParty": {
                "embedUrl": "https://www.google.com",
            },
        },
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "api_key": "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
    },
    {
        "name": "WEB_EMBEDDED",
        "context": {
            "client": {
                "clientName": "WEB_EMBEDDED_PLAYER",
                "clientVersion": "1.20250310.00.00",
            },
            "thirdParty": {
                "embedUrl": "https://www.google.com",
            },
        },
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "api_key": "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
    },
]


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


def _parse_iso_duration(iso_str: str) -> int:
    """Parse ISO 8601 duration (PT1H2M3S) to total seconds."""
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_str)
    if not m:
        return 0
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)


def _build_proxy_transport() -> httpx.AsyncHTTPTransport | None:
    """Build proxy transport for requests to www.youtube.com (blocked from datacenter IPs)."""
    if _WEBSHARE_PROXY_USER and _WEBSHARE_PROXY_PASS:
        proxy_url = f"http://{_WEBSHARE_PROXY_USER}:{_WEBSHARE_PROXY_PASS}@p.webshare.io:80"
        return httpx.AsyncHTTPTransport(proxy=proxy_url)
    if _YOUTUBE_PROXY_URL:
        return httpx.AsyncHTTPTransport(proxy=_YOUTUBE_PROXY_URL)
    return None


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
        Fetch video metadata. Tries YouTube Data API v3 first (reliable from
        datacenter IPs via googleapis.com), falls back to oembed endpoint.

        Args:
            video_id: 11-character YouTube video ID.

        Returns:
            Dict with videoId, url, title, channel, thumbnail.
            When using API: also includes duration_seconds, has_captions.

        Raises:
            VideoNotFoundError: If video does not exist or is private.
            TranscriptionServiceError: On unexpected HTTP errors.
        """
        if _YOUTUBE_API_KEY:
            try:
                return await YouTubeService._get_metadata_via_api(video_id)
            except VideoNotFoundError:
                raise
            except Exception as e:
                logger.warning(f"YouTube Data API failed, falling back to oembed: {e}")
        return await YouTubeService._get_metadata_via_oembed(video_id)

    @staticmethod
    async def _get_metadata_via_api(video_id: str) -> dict:
        """Fetch video metadata via YouTube Data API v3 (requires YOUTUBE_API_KEY)."""
        api_url = (
            f"https://www.googleapis.com/youtube/v3/videos"
            f"?part=snippet,contentDetails&id={video_id}&key={_YOUTUBE_API_KEY}"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url)

        if response.status_code == 403:
            raise TranscriptionServiceError("YouTube API quota exceeded or key invalid.")

        if response.status_code != 200:
            raise TranscriptionServiceError(
                f"YouTube Data API returned status {response.status_code}"
            )

        data = response.json()
        items = data.get("items", [])
        if not items:
            raise VideoNotFoundError("Vídeo não encontrado ou é privado.")

        item = items[0]
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})
        thumbnails = snippet.get("thumbnails", {})

        thumbnail_url = (
            thumbnails.get("maxres", {}).get("url")
            or thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        )

        return {
            "videoId": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "thumbnail": thumbnail_url,
            "duration_seconds": _parse_iso_duration(
                content_details.get("duration", "PT0S")
            ),
        }

    @staticmethod
    async def _get_metadata_via_oembed(video_id: str) -> dict:
        """Fetch video metadata from YouTube oembed endpoint (fallback)."""
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
    def _build_result(
        raw_segments: list[dict],
        language: str,
        caption_type: str,
        target_duration: float,
    ) -> dict:
        """Build the final caption result dict from raw segments."""
        last = raw_segments[-1]
        total_duration = last.get("start", 0) + last.get("duration", 0)
        merged = YouTubeService._merge_segments(raw_segments, target_duration)
        return {
            "segments": merged,
            "language": language,
            "caption_type": caption_type,
            "total_duration_seconds": int(total_duration),
        }

    @staticmethod
    async def get_captions(
        video_id: str,
        languages: Optional[list[str]] = None,
        target_duration: float = 45.0,
    ) -> dict:
        """
        Fetch and merge captions for a YouTube video.

        Strategy (tried in order):
        1. InnerTube Player API via googleapis.com (proxy-free, ANDROID+WEB)
        2. youtube-transcript-api library (with proxy if configured)
        3. Timedtext endpoint (last resort)

        Args:
            video_id: 11-character YouTube video ID.
            languages: Language priority list. Defaults to ["pt", "pt-BR", "en", "es"].
            target_duration: Target duration per merged segment in seconds.

        Returns:
            Dict with segments, language, caption_type, total_duration_seconds.

        Raises:
            CaptionsNotAvailableError: If no captions are available.
            VideoNotFoundError: If video is unavailable.
            TranscriptionServiceError: On unexpected errors.
        """
        if languages is None:
            languages = DEFAULT_LANGUAGES

        # ── Strategy 1: InnerTube Player API (proxy-free) ──
        logger.info(f"Trying InnerTube API for {video_id}")
        innertube_result = await YouTubeService._fetch_captions_innertube(
            video_id, languages
        )
        if innertube_result is not None:
            raw_segments, language, caption_type = innertube_result
            if raw_segments:
                return YouTubeService._build_result(
                    raw_segments, language, caption_type, target_duration
                )

        logger.info(
            f"InnerTube did not return captions for {video_id}, "
            f"trying youtube-transcript-api"
        )

        # ── Strategy 2: youtube-transcript-api (with proxy if available) ──
        def _fetch_transcript():
            """Synchronous call to youtube_transcript_api v1.x (runs in thread)."""
            from youtube_transcript_api import YouTubeTranscriptApi

            proxy_config = None
            if _WEBSHARE_PROXY_USER and _WEBSHARE_PROXY_PASS:
                from youtube_transcript_api.proxies import WebshareProxyConfig
                proxy_config = WebshareProxyConfig(
                    proxy_username=_WEBSHARE_PROXY_USER,
                    proxy_password=_WEBSHARE_PROXY_PASS,
                )
                logger.debug("Using Webshare proxy for YouTube transcript")
            elif _YOUTUBE_PROXY_URL:
                from youtube_transcript_api.proxies import GenericProxyConfig
                proxy_config = GenericProxyConfig(
                    https_url=_YOUTUBE_PROXY_URL,
                    http_url=_YOUTUBE_PROXY_URL,
                )
                logger.debug("Using generic proxy for YouTube transcript")

            api = (
                YouTubeTranscriptApi(proxy_config=proxy_config)
                if proxy_config
                else YouTubeTranscriptApi()
            )

            first_error = None
            try:
                result = api.fetch(video_id, languages=languages)
                raw = result.to_raw_data()
                detected_language = result.language_code
                caption_type = (
                    "auto-generated" if result.is_generated else "manual"
                )
                return raw, detected_language, caption_type
            except Exception as e:
                first_error = e
                logger.debug(
                    f"api.fetch failed for {video_id}: "
                    f"{type(e).__name__}: {e}"
                )

            try:
                transcript_list = api.list(video_id)
            except Exception as e:
                logger.warning(
                    f"api.list also failed for {video_id}: "
                    f"{type(e).__name__}: {e}"
                )
                raise first_error or e

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

            raise Exception("NoTranscriptFound")

        try:
            raw_segments, language, caption_type = await asyncio.to_thread(
                _fetch_transcript
            )
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            error_full = f"{error_type}: {error_msg}"

            # Definitive errors — no point trying timedtext fallback
            if (
                "TranscriptsDisabled" in error_type
                or "TranscriptsDisabled" in error_msg
            ):
                raise CaptionsNotAvailableError(
                    "Este vídeo não possui legendas disponíveis."
                )
            elif (
                "NoTranscriptFound" in error_type
                or "NoTranscriptFound" in error_msg
            ):
                # Not definitive from datacenter — youtube-transcript-api may
                # fail to list transcripts even when they exist. Try timedtext.
                logger.warning(
                    f"NoTranscriptFound for {video_id} via youtube-transcript-api, "
                    f"trying timedtext fallback"
                )
            elif (
                "VideoUnavailable" in error_type
                or "VideoUnavailable" in error_msg
            ):
                raise VideoNotFoundError(
                    "Vídeo não encontrado ou é privado."
                )
            elif (
                "InvalidVideoId" in error_type
                or "InvalidVideoId" in error_msg
            ):
                raise VideoNotFoundError("ID de vídeo inválido.")
            elif "AgeRestricted" in error_type or "age" in error_msg.lower():
                raise CaptionsNotAvailableError(
                    "Este vídeo possui restrição de idade e não pode ser "
                    "transcrito."
                )
            elif (
                "CouldNotRetrieveTranscript" in error_type
                or "CouldNotRetrieveTranscript" in error_msg
            ):
                if (
                    "disabled" in error_msg.lower()
                    or "subtitles" in error_msg.lower()
                ):
                    raise CaptionsNotAvailableError(
                        "Este vídeo não possui legendas disponíveis."
                    )
                raise CaptionsNotAvailableError(
                    "Não foi possível obter as legendas deste vídeo."
                )

            # Transient/blocking errors — try timedtext fallback
            if (
                "RequestBlocked" in error_type
                or "RequestBlocked" in error_msg
            ):
                logger.warning(
                    f"youtube-transcript-api blocked for {video_id}, "
                    f"trying timedtext fallback"
                )
            elif (
                "TooManyRequests" in error_type
                or "TooManyRequests" in error_msg
            ):
                logger.warning(
                    f"YouTube rate-limited for {video_id}, "
                    f"trying timedtext fallback"
                )
            elif "FailedToCreateConsentCookie" in error_type:
                logger.warning(
                    f"Consent cookie issue for {video_id}, "
                    f"trying timedtext fallback"
                )
            else:
                logger.warning(
                    f"youtube-transcript-api error for {video_id}: "
                    f"{error_full}, trying timedtext fallback"
                )

            # ── Strategy 3: Timedtext endpoint (last resort) ──
            timedtext_result = await YouTubeService._fetch_captions_timedtext(
                video_id, languages
            )
            if timedtext_result is not None:
                raw_fb, lang_fb, type_fb = timedtext_result
                if raw_fb:
                    return YouTubeService._build_result(
                        raw_fb, lang_fb, type_fb, target_duration
                    )

            # All strategies exhausted
            if (
                "RequestBlocked" in error_type
                or "RequestBlocked" in error_msg
            ):
                raise TranscriptionServiceError(
                    "YouTube bloqueou a requisição de legendas. "
                    "Tente novamente em alguns minutos."
                )
            elif (
                "TooManyRequests" in error_type
                or "TooManyRequests" in error_msg
            ):
                raise TranscriptionServiceError(
                    "YouTube limitou as requisições. "
                    "Tente novamente em alguns minutos."
                )
            elif (
                "NoTranscriptFound" in error_type
                or "NoTranscriptFound" in error_msg
            ):
                raise CaptionsNotAvailableError(
                    "Não foram encontradas legendas nos idiomas suportados "
                    "(pt, en, es)."
                )
            else:
                raise TranscriptionServiceError(
                    f"Erro ao buscar legendas do YouTube. ({error_type})"
                )

        if not raw_segments:
            raise CaptionsNotAvailableError(
                "Este vídeo não possui legendas disponíveis."
            )

        return YouTubeService._build_result(
            raw_segments, language, caption_type, target_duration
        )

    @staticmethod
    def _parse_json3_events(events: list[dict]) -> list[dict]:
        """Parse JSON3 caption events into normalized segments."""
        segments = []
        for event in events:
            segs = event.get("segs")
            if not segs:
                continue
            text = "".join(s.get("utf8", "") for s in segs).strip()
            if not text or text == "\n":
                continue
            segments.append({
                "text": text,
                "start": event.get("tStartMs", 0) / 1000.0,
                "duration": event.get("dDurationMs", 0) / 1000.0,
            })
        return segments

    @staticmethod
    def _parse_xml_captions(xml_text: str) -> list[dict]:
        """
        Parse YouTube's XML caption format into normalized segments.

        YouTube now returns XML instead of JSON3 from timedtext endpoints:
        <timedtext format="3">
          <body>
            <p t="1360" d="1680">caption text</p>
          </body>
        </timedtext>

        where t=start time in ms, d=duration in ms.
        """
        segments = []
        try:
            root = ET.fromstring(xml_text)
            body = root.find("body")
            if body is None:
                # Some responses have <p> directly under root
                paragraphs = root.findall(".//p")
            else:
                paragraphs = body.findall("p")

            for p in paragraphs:
                # Get text content including nested <s> elements
                text_parts = []
                if p.text:
                    text_parts.append(p.text)
                for child in p:
                    if child.text:
                        text_parts.append(child.text)
                    if child.tail:
                        text_parts.append(child.tail)

                text = unescape("".join(text_parts)).strip()
                if not text or text == "\n":
                    continue

                t_ms = int(p.get("t", "0"))
                d_ms = int(p.get("d", "0"))

                segments.append({
                    "text": text,
                    "start": t_ms / 1000.0,
                    "duration": d_ms / 1000.0,
                })
        except ET.ParseError as e:
            logger.debug(f"XML caption parse error: {e}")
        return segments

    @staticmethod
    def _parse_caption_response(response: httpx.Response) -> list[dict]:
        """
        Parse a caption response, handling both JSON3 and XML formats.

        YouTube recently changed timedtext to return XML even when fmt=json3
        is requested. This method detects the format and parses accordingly.
        """
        content_type = response.headers.get("content-type", "")
        text = response.text

        # Try JSON3 first (legacy format)
        if "application/json" in content_type or text.lstrip().startswith("{"):
            try:
                data = response.json()
                events = data.get("events", [])
                return YouTubeService._parse_json3_events(events)
            except Exception:
                pass

        # Try XML (current YouTube format)
        if "xml" in content_type or text.lstrip().startswith("<?xml") or text.lstrip().startswith("<timedtext"):
            return YouTubeService._parse_xml_captions(text)

        # Last resort: try both parsers
        try:
            data = response.json()
            events = data.get("events", [])
            segments = YouTubeService._parse_json3_events(events)
            if segments:
                return segments
        except Exception:
            pass

        return YouTubeService._parse_xml_captions(text)

    @staticmethod
    async def _fetch_captions_innertube(
        video_id: str,
        languages: list[str],
    ) -> tuple[list[dict], str, str] | None:
        """
        Fetch captions via YouTube InnerTube Player API (googleapis.com).

        Uses the InnerTube `/player` endpoint which returns caption track URLs
        with embedded auth tokens. The googleapis.com domain is NOT blocked
        from datacenter IPs. Tries ANDROID client first, then WEB.

        Returns (raw_segments, language, caption_type) or None on failure.
        """
        for client_cfg in _INNERTUBE_CLIENTS:
            try:
                player_url = (
                    f"https://youtubei.googleapis.com/youtubei/v1/player"
                    f"?key={client_cfg['api_key']}&prettyPrint=false"
                )
                player_body = {
                    "context": client_cfg["context"],
                    "videoId": video_id,
                    "contentCheckOk": True,
                    "racyCheckOk": True,
                }
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": client_cfg["user_agent"],
                }

                async with httpx.AsyncClient(timeout=15.0) as http:
                    resp = await http.post(
                        player_url, json=player_body, headers=headers
                    )

                if resp.status_code != 200:
                    logger.debug(
                        f"InnerTube player ({client_cfg['name']}) returned "
                        f"{resp.status_code} for {video_id}"
                    )
                    continue

                player_data = resp.json()

                # Check for playability errors (but still try captions)
                status = player_data.get("playabilityStatus", {})
                playability = status.get("status", "")
                if playability == "ERROR":
                    logger.debug(
                        f"InnerTube playability error for {video_id}: "
                        f"{status.get('reason', 'unknown')}"
                    )
                    continue
                elif playability not in ("OK", ""):
                    logger.debug(
                        f"InnerTube ({client_cfg['name']}) playability={playability} "
                        f"for {video_id}, still checking captions"
                    )

                # Extract caption tracks
                captions = player_data.get("captions", {})
                renderer = captions.get("playerCaptionsTracklistRenderer", {})
                caption_tracks = renderer.get("captionTracks", [])
                logger.debug(
                    f"InnerTube ({client_cfg['name']}) for {video_id}: "
                    f"playability={playability}, "
                    f"caption_tracks={len(caption_tracks)}, "
                    f"has_captions_key={'captions' in player_data}"
                )

                if not caption_tracks:
                    logger.debug(
                        f"InnerTube ({client_cfg['name']}): no caption tracks "
                        f"for {video_id}"
                    )
                    continue

                # Find best matching track by language priority
                selected_track = None
                selected_lang = None
                selected_type = "manual"

                for lang in languages:
                    # Prefer manual captions over auto-generated
                    for track in caption_tracks:
                        lang_code = track.get("languageCode", "")
                        if lang_code == lang or lang_code.startswith(f"{lang}-"):
                            if track.get("kind") != "asr":
                                selected_track = track
                                selected_lang = lang_code
                                selected_type = "manual"
                                break
                    if selected_track:
                        break
                    # Then try auto-generated
                    for track in caption_tracks:
                        lang_code = track.get("languageCode", "")
                        if lang_code == lang or lang_code.startswith(f"{lang}-"):
                            selected_track = track
                            selected_lang = lang_code
                            selected_type = (
                                "auto-generated"
                                if track.get("kind") == "asr"
                                else "manual"
                            )
                            break
                    if selected_track:
                        break

                if not selected_track:
                    # Fallback: accept the first available track regardless
                    # of language — better to return captions in an unexpected
                    # language than to fail entirely
                    available_langs = [
                        t.get("languageCode") for t in caption_tracks
                    ]
                    logger.info(
                        f"InnerTube ({client_cfg['name']}): no exact language "
                        f"match for {video_id}, available: {available_langs}. "
                        f"Falling back to first available track."
                    )
                    selected_track = caption_tracks[0]
                    selected_lang = selected_track.get("languageCode", "unknown")
                    selected_type = (
                        "auto-generated"
                        if selected_track.get("kind") == "asr"
                        else "manual"
                    )

                # Fetch caption content from authenticated baseUrl
                # The baseUrl points to www.youtube.com which may be blocked
                # from datacenter IPs — try direct first, then with proxy
                base_url = selected_track["baseUrl"]
                subtitle_url = f"{base_url}&fmt=json3"
                sub_headers = {"User-Agent": client_cfg["user_agent"]}

                sub_resp = None
                # Attempt 1: Direct (works from residential IPs)
                try:
                    async with httpx.AsyncClient(timeout=10.0) as http:
                        sub_resp = await http.get(
                            subtitle_url, headers=sub_headers
                        )
                    if sub_resp.status_code != 200:
                        logger.debug(
                            f"InnerTube direct caption fetch: "
                            f"HTTP {sub_resp.status_code} for {video_id}"
                        )
                        sub_resp = None
                except Exception as e:
                    logger.debug(
                        f"InnerTube direct caption fetch failed: {e}"
                    )

                # Attempt 2: With proxy (for datacenter IPs)
                if sub_resp is None:
                    transport = _build_proxy_transport()
                    if transport:
                        try:
                            async with httpx.AsyncClient(
                                timeout=15.0, transport=transport
                            ) as http:
                                sub_resp = await http.get(
                                    subtitle_url, headers=sub_headers
                                )
                            if sub_resp.status_code != 200:
                                logger.debug(
                                    f"InnerTube proxy caption fetch: "
                                    f"HTTP {sub_resp.status_code}"
                                )
                                sub_resp = None
                        except Exception as e:
                            logger.debug(
                                f"InnerTube proxy caption fetch failed: {e}"
                            )

                if sub_resp is None or sub_resp.status_code != 200:
                    logger.debug(
                        f"InnerTube caption content fetch failed "
                        f"for {video_id} (all attempts)"
                    )
                    continue

                # Parse response (handles both JSON3 and XML formats)
                segments = YouTubeService._parse_caption_response(sub_resp)

                if not segments:
                    logger.debug(
                        f"InnerTube ({client_cfg['name']}): empty segments "
                        f"after parse for {video_id}"
                    )
                    continue

                logger.info(
                    f"InnerTube ({client_cfg['name']}) captions succeeded for "
                    f"{video_id}: lang={selected_lang}, type={selected_type}, "
                    f"{len(segments)} raw segments"
                )
                return segments, selected_lang, selected_type

            except Exception as e:
                logger.debug(
                    f"InnerTube ({client_cfg['name']}) failed for "
                    f"{video_id}: {type(e).__name__}: {e}"
                )
                continue

        return None

    @staticmethod
    async def _fetch_captions_timedtext(
        video_id: str,
        languages: list[str],
    ) -> tuple[list[dict], str, str] | None:
        """
        Last-resort fallback: fetch captions via YouTube's public timedtext
        endpoint. Uses configured proxy if available. Returns (raw_segments,
        language, caption_type) or None if all attempts fail.
        """
        transport = _build_proxy_transport()

        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                transport=transport,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                },
            ) as client:
                for lang in languages:
                    for kind, caption_type in [("", "manual"), ("asr", "auto-generated")]:
                        params = {"v": video_id, "lang": lang, "fmt": "json3"}
                        if kind:
                            params["kind"] = kind

                        url = "https://www.youtube.com/api/timedtext"
                        resp = await client.get(url, params=params)

                        if resp.status_code != 200:
                            continue

                        # Parse response (handles both JSON3 and XML)
                        segments = YouTubeService._parse_caption_response(resp)

                        if segments:
                            logger.info(
                                f"Timedtext fallback succeeded for {video_id}: "
                                f"lang={lang}, type={caption_type}, "
                                f"{len(segments)} raw segments"
                            )
                            return segments, lang, caption_type

        except Exception as e:
            logger.debug(f"Timedtext fallback failed for {video_id}: {e}")

        return None

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
