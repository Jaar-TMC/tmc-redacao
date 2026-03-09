# SPEC: YouTube Transcription Route (Legendas)

**Status:** APPROVED
**Author:** Enzo (via Claude)
**Date:** 2026-03-09
**Complexity:** Low
**Estimated Effort:** 3-5 hours across 2 teams

---

## 1. Vision

Enable journalists to paste a YouTube video URL and receive timestamped transcription segments from YouTube's built-in captions (legendas). This replaces the current mock data in `TranscricaoPage` with a real backend service, completing the video-to-article workflow already designed in the frontend.

**Non-goals:**
- Audio-to-text transcription (Whisper, AssemblyAI) — out of scope
- Video download or audio extraction — not needed
- Speaker diarization — not needed for v1
- Support for non-YouTube video platforms

---

## 2. Architecture Overview

```
┌─────────────────────┐     POST /api/transcribe      ┌──────────────────────────┐
│   TranscricaoPage   │ ──────────────────────────────▶│  transcription_api.py    │
│   (React Frontend)  │                                │  (Azure Function)        │
│                     │◀──────────────────────────────│                          │
│   YouTubeInput.jsx  │     { video, transcription }   │  youtube_service.py      │
│                     │                                │  (Caption Fetcher)       │
└─────────────────────┘                                └──────────────────────────┘
                                                                │
                                                                ▼
                                                       YouTube Caption API
                                                       (via youtube-transcript-api)
```

**Data flow:**
1. User pastes YouTube URL → frontend validates format (regex, already exists)
2. Frontend calls `POST /api/transcribe` with `{ url }`
3. Backend extracts video ID, fetches metadata + captions from YouTube
4. Backend returns `{ video, transcription }` in the exact schema `CriarContext` expects
5. Frontend saves to context via `setFonte('transcription', data)` and navigates to `/criar/texto-base`

---

## 3. Team Assignments

### Team BACKEND — Python Azure Functions
**Files to create:**
- `FeedRSS/tmc-rss-collector/services/youtube_service.py`
- `FeedRSS/tmc-rss-collector/functions/transcription_api.py`

**Files to modify:**
- `FeedRSS/tmc-rss-collector/function_app.py` (register new route)
- `FeedRSS/tmc-rss-collector/requirements.txt` (add dependency)

### Team FRONTEND — React/Vite
**Files to modify:**
- `tmc-redacao/src/services/api.js` (add `transcribeVideo` function)
- `tmc-redacao/src/pages/transcricao/TranscricaoPage.jsx` (replace mock with API call)
- `tmc-redacao/src/pages/transcricao/components/YouTubeInput.jsx` (real validation via API)
- `tmc-redacao/src/pages/transcricao/components/ProgressOverlay.jsx` (update status messages)

---

## 4. Backend Spec (Team BACKEND)

### 4.1 Dependency

Add to `requirements.txt`:
```
youtube-transcript-api==0.6.3
```

This is a pure-Python library that fetches YouTube auto-generated and manual captions without needing `ffmpeg`, `yt-dlp`, or YouTube Data API keys. It works by calling YouTube's internal timedtext endpoint.

### 4.2 Service: `services/youtube_service.py`

```python
"""
YouTube Service - Fetches video metadata and captions from YouTube.

Uses youtube-transcript-api for caption retrieval.
No API key required. No audio processing.
"""
```

**Class: `YouTubeService`**

#### Method: `extract_video_id(url: str) -> str | None`

- Parse video ID from YouTube URL formats:
  - `https://www.youtube.com/watch?v=XXXXXXXXXXX`
  - `https://youtu.be/XXXXXXXXXXX`
  - `https://www.youtube.com/embed/XXXXXXXXXXX`
  - `https://www.youtube.com/shorts/XXXXXXXXXXX`
- Return 11-char video ID or `None` if invalid
- Use regex: `r'(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})'`

#### Method: `async get_video_metadata(video_id: str) -> dict`

- Fetch video metadata using an HTTP GET to `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json`
- This is a free, no-auth-needed endpoint that returns:
  ```json
  {
    "title": "Video Title",
    "author_name": "Channel Name",
    "author_url": "https://www.youtube.com/@channel",
    "thumbnail_url": "https://i.ytimg.com/vi/VIDEO_ID/hqdefault.jpg"
  }
  ```
- Map to our schema:
  ```python
  {
      "videoId": video_id,
      "url": original_url,
      "title": oembed["title"],
      "channel": oembed["author_name"],
      "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
  }
  ```
- If oembed fails (404 = video doesn't exist, or is private), raise `VideoNotFoundError`
- Use `httpx` (already in requirements) for the HTTP call
- **Timeout:** 10 seconds

#### Method: `async get_captions(video_id: str, languages: list[str] = None) -> list[dict]`

- Use `youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id, languages=languages)`
- Default languages priority: `["pt", "pt-BR", "en", "es"]`
- The library returns a list of dicts:
  ```python
  [
      {"text": "Olá, sejam bem-vindos", "start": 0.0, "duration": 5.2},
      {"text": "Hoje vamos falar sobre", "start": 5.2, "duration": 3.1},
      ...
  ]
  ```
- **Transform** into our segment format (merge short fragments into ~30-60s segments):

  ```python
  def _merge_segments(raw_segments: list[dict], target_duration: float = 45.0) -> list[dict]:
      """
      Merge YouTube's fine-grained caption fragments (~2-5s each)
      into meaningful segments of ~30-60 seconds.

      Returns segments in the format CriarContext expects:
      {
          "id": "1",
          "startTime": "00:00",
          "endTime": "00:45",
          "text": "Merged text content...",
          "topic": ""  # Empty - frontend can optionally extract topics later
      }
      """
  ```

  **Merge algorithm:**
  1. Accumulate fragments into a buffer
  2. When accumulated duration >= `target_duration` AND the next fragment starts a new sentence (capital letter or period in previous), flush the buffer as a segment
  3. Final buffer always flushed as last segment
  4. Format `startTime`/`endTime` as `"MM:SS"` or `"HH:MM:SS"` if >= 1 hour
  5. `topic` field left as empty string (the existing topic extraction flow on the frontend can handle this optionally)

- **Error handling:**
  - `TranscriptsDisabled` → raise `CaptionsNotAvailableError("Este vídeo não possui legendas disponíveis.")`
  - `NoTranscriptFound` → raise `CaptionsNotAvailableError("Não foram encontradas legendas nos idiomas suportados (pt, en, es).")`
  - `VideoUnavailable` → raise `VideoNotFoundError("Vídeo não encontrado ou é privado.")`
  - Generic exception → log and raise `TranscriptionServiceError("Erro ao buscar legendas do YouTube.")`

#### Custom Exceptions

```python
class VideoNotFoundError(Exception):
    """Video does not exist or is private."""
    pass

class CaptionsNotAvailableError(Exception):
    """Video exists but has no captions in supported languages."""
    pass

class TranscriptionServiceError(Exception):
    """Generic service error."""
    pass
```

### 4.3 Function: `functions/transcription_api.py`

```python
"""
Transcription API - Azure Functions endpoint for YouTube caption transcription.

Endpoint:
- POST /api/transcribe - Fetch YouTube captions for a video URL
"""
```

#### Handler: `transcribe_handler(req: HttpRequest) -> HttpResponse`

**Request validation (Pydantic):**
```python
class TranscribeRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)
    languages: list[str] | None = Field(None, max_length=5)
    segment_duration: float = Field(default=45.0, ge=15.0, le=120.0)
```

**Flow:**
1. Parse and validate request body
2. Run prompt injection check on `url` field (reuse `_INJECTION_PATTERNS` from `generation_api.py` — import or share via utility)
3. Extract video ID → 400 if invalid
4. Fetch metadata → 404 if `VideoNotFoundError`
5. Fetch captions → 422 if `CaptionsNotAvailableError`
6. Return response

**Success response (200):**
```json
{
  "video": {
    "videoId": "dQw4w9WgXcQ",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Video Title Here",
    "channel": "Channel Name",
    "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
  },
  "transcription": [
    {
      "id": "1",
      "startTime": "00:00",
      "endTime": "00:45",
      "text": "Merged caption text for this segment...",
      "topic": ""
    },
    {
      "id": "2",
      "startTime": "00:45",
      "endTime": "01:32",
      "text": "Next segment of captions...",
      "topic": ""
    }
  ],
  "metadata": {
    "language": "pt",
    "total_segments": 12,
    "total_duration_seconds": 932,
    "caption_type": "auto-generated"
  }
}
```

**Error responses:**

| Status | Condition | Body |
|--------|-----------|------|
| 400 | Invalid URL format | `{"error": "URL inválida. Forneça um link válido do YouTube."}` |
| 400 | Injection detected | `{"error": "Entrada inválida."}` |
| 404 | Video not found | `{"error": "Vídeo não encontrado ou é privado."}` |
| 422 | No captions available | `{"error": "Este vídeo não possui legendas disponíveis.", "details": "..."}` |
| 429 | Rate limited | `{"error": "Rate limit exceeded", "retry_after_seconds": N}` |
| 500 | Internal error | `{"error": "Erro interno ao processar transcrição."}` |

### 4.4 Route Registration in `function_app.py`

Add after the `edit-article` route block (line ~606):

```python
# ========================================
# HTTP TRIGGERS - TRANSCRIPTION API
# ========================================

@app.route(route="transcribe", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
async def transcribe_video(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/transcribe - Fetch YouTube captions for a video URL.

    Body:
        {
            "url": "https://www.youtube.com/watch?v=VIDEO_ID",
            "languages": ["pt", "en"],  // optional
            "segment_duration": 45.0     // optional, seconds per merged segment
        }

    Returns:
        {
            "video": { videoId, url, title, channel, thumbnail },
            "transcription": [ { id, startTime, endTime, text, topic } ],
            "metadata": { language, total_segments, total_duration_seconds, caption_type }
        }
    """
    from services.rate_limiter import RateLimiter
    retry_after = RateLimiter.get().check("transcribe")
    if retry_after is not None:
        import json as _json
        return func.HttpResponse(
            _json.dumps({"error": "Rate limit exceeded", "retry_after_seconds": round(retry_after, 1)}),
            status_code=429,
            headers={"Retry-After": str(int(retry_after) + 1)},
            mimetype="application/json",
        )
    from functions.transcription_api import transcribe_handler
    return await transcribe_handler(req)
```

Also add to the startup log block:
```python
logger.info("  - POST /api/transcribe")
```

### 4.5 Rate Limiting

Register in the rate limiter config (same pattern as other endpoints):
- **Window:** 60 seconds
- **Max requests:** 10 per user
- **Rationale:** YouTube caption fetches are fast (~1-3s) but we don't want abuse

### 4.6 Security Considerations

- **No API keys needed** — `youtube-transcript-api` uses YouTube's public timedtext endpoint
- **No data stored** — transcriptions are returned to the client, not persisted in DB
- **Input validation** — URL validated via regex + Pydantic, injection patterns checked
- **Auth required** — `@require_auth` decorator ensures only authenticated users can call
- **No SSRF risk** — we only call known YouTube domains (oembed + timedtext)

---

## 5. Frontend Spec (Team FRONTEND)

### 5.1 API Function: `services/api.js`

Add new exported function:

```javascript
// ============================================
// Transcription API
// ============================================

/**
 * Transcribe a YouTube video by fetching its captions
 * @param {Object} params - Transcription parameters
 * @param {string} params.url - YouTube video URL
 * @param {string[]} [params.languages] - Preferred languages (default: ["pt", "en", "es"])
 * @param {number} [params.segment_duration] - Target segment duration in seconds (default: 45)
 * @param {Object} [options] - Fetch options
 * @param {AbortSignal} [options.signal] - AbortController signal for cancellation
 * @returns {Promise<{
 *   video: { videoId: string, url: string, title: string, channel: string, thumbnail: string },
 *   transcription: Array<{ id: string, startTime: string, endTime: string, text: string, topic: string }>,
 *   metadata: { language: string, total_segments: number, total_duration_seconds: number, caption_type: string }
 * }>}
 */
export async function transcribeVideo(params, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

  try {
    const response = await fetchApi('/transcribe', {
      method: 'POST',
      body: JSON.stringify(params),
      signal: options.signal || controller.signal,
    });
    return response;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('A transcrição excedeu o tempo limite. Tente novamente.');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}
```

Add to the default export object:
```javascript
transcribeVideo,
```

### 5.2 YouTubeInput.jsx — Real Validation

Replace the mock validation in `validateURL` with a lightweight check:

**Keep:** The regex-based format validation (instant feedback)
**Change:** On valid format, instead of mock data, call the oembed endpoint client-side for preview:

```javascript
// After regex validation passes:
const videoId = extractVideoId(url);

// Use YouTube oembed for instant metadata (no backend needed for preview)
try {
  const oembedRes = await fetch(
    `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`
  );

  if (!oembedRes.ok) {
    setStatus('invalid');
    setError('Vídeo não encontrado ou é privado.');
    onValidURL(null);
    return;
  }

  const oembed = await oembedRes.json();

  setStatus('valid');
  onValidURL({
    videoId,
    url,
    title: oembed.title,
    channel: oembed.author_name,
    thumbnail: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
  });
} catch {
  setStatus('invalid');
  setError('Não foi possível verificar este vídeo.');
  onValidURL(null);
}
```

**Why client-side oembed?** It validates that the video actually exists without hitting our backend. The `POST /api/transcribe` does the full validation + caption fetch later.

### 5.3 TranscricaoPage.jsx — Replace Mock with API Call

Replace `handleStartTranscription`:

```javascript
import { transcribeVideo } from '../../services/api';

const handleStartTranscription = useCallback(async () => {
  if (!videoData) return;

  setIsTranscribing(true);
  setTranscriptionProgress(0);
  setTranscriptionError(null);
  nextStep(); // Go to step 2 (loading)

  // Simulate smooth progress while waiting for API
  const progressInterval = setInterval(() => {
    setTranscriptionProgress(prev => {
      if (prev >= 90) return prev; // Cap at 90% until API responds
      return prev + Math.random() * 12;
    });
  }, 400);

  try {
    const result = await transcribeVideo({ url: videoData.url });

    clearInterval(progressInterval);
    setTranscriptionProgress(100);

    // Convert transcription to selections format
    const allSelections = result.transcription.map(segment => ({
      id: `card-${segment.id}`,
      text: segment.text,
      source: 'cards',
      topic: segment.topic,
      timestamp: segment.startTime,
    }));

    setTimeout(() => {
      setIsTranscribing(false);

      setFonte('transcription', {
        video: result.video,
        transcription: result.transcription,
        selections: allSelections,
      });

      navigate('/criar/texto-base');
    }, 500);
  } catch (err) {
    clearInterval(progressInterval);
    setIsTranscribing(false);

    // Map API error codes to user-friendly messages
    let errorMessage = 'Ocorreu um erro ao transcrever o vídeo. Tente novamente.';
    if (err?.status === 422) {
      errorMessage = err.data?.error || 'Este vídeo não possui legendas disponíveis.';
    } else if (err?.status === 404) {
      errorMessage = 'Vídeo não encontrado ou é privado.';
    } else if (err?.status === 429) {
      errorMessage = 'Muitas requisições. Aguarde um momento e tente novamente.';
    }

    setTranscriptionError(errorMessage);
    goToStep(1);
  }
}, [videoData, nextStep, goToStep, setFonte, navigate]);
```

**Delete:** The `MOCK_TRANSCRIPTION` constant at the top of the file.

### 5.4 ProgressOverlay.jsx — Update Messages

Change the progress messages from audio-processing language to caption-fetching language:

```javascript
const messages = [
  'Conectando ao YouTube...',
  'Buscando legendas do vídeo...',
  'Processando transcrição...',
  'Organizando segmentos...',
  'Finalizando...'
];
```

### 5.5 TipBox Update

In `TranscricaoPage.jsx`, the existing TipBox text is already correct:
```
"Funciona melhor com vídeos que possuem legendas ou áudio claro em português/inglês"
```

Update to be more precise since we only support captions:
```
"Funciona com vídeos que possuem legendas (automáticas ou manuais) em português, inglês ou espanhol"
```

---

## 6. Data Contract (Shared Schema)

This is the **single source of truth** for the data shape between backend and frontend.

### Request
```typescript
interface TranscribeRequest {
  url: string;                    // YouTube URL (required)
  languages?: string[];           // Language priority (default: ["pt", "pt-BR", "en", "es"])
  segment_duration?: number;      // Target seconds per segment (default: 45, min: 15, max: 120)
}
```

### Response
```typescript
interface TranscribeResponse {
  video: {
    videoId: string;              // 11-char YouTube video ID
    url: string;                  // Original URL provided by user
    title: string;                // Video title from YouTube
    channel: string;              // Channel name from YouTube
    thumbnail: string;            // Thumbnail URL (maxresdefault)
  };
  transcription: Array<{
    id: string;                   // Sequential: "1", "2", "3"...
    startTime: string;            // "MM:SS" or "HH:MM:SS"
    endTime: string;              // "MM:SS" or "HH:MM:SS"
    text: string;                 // Merged caption text
    topic: string;                // Empty string (placeholder for future topic extraction)
  }>;
  metadata: {
    language: string;             // Caption language used (e.g., "pt", "en")
    total_segments: number;       // Number of merged segments
    total_duration_seconds: number; // Total video duration in seconds
    caption_type: string;         // "manual" | "auto-generated"
  };
}
```

### Compatibility with CriarContext

The response maps directly to `CriarContext.fonte`:
```javascript
setFonte('transcription', {
  video: response.video,           // ✅ Matches existing videoData shape
  transcription: response.transcription, // ✅ Matches MOCK_TRANSCRIPTION shape
  selections: response.transcription.map(s => ({
    id: `card-${s.id}`,
    text: s.text,
    source: 'cards',
    topic: s.topic,
    timestamp: s.startTime,
  })),
});
```

---

## 7. Task Breakdown

### Team BACKEND (3 tasks, ~2-3h)

| # | Task | File | Est. |
|---|------|------|------|
| B1 | Create `YouTubeService` with `extract_video_id`, `get_video_metadata`, `get_captions`, `_merge_segments` | `services/youtube_service.py` | 45min |
| B2 | Create `transcribe_handler` with Pydantic validation, error handling, and response formatting | `functions/transcription_api.py` | 30min |
| B3 | Register route in `function_app.py`, add `youtube-transcript-api` to `requirements.txt`, add startup log line | `function_app.py`, `requirements.txt` | 15min |

### Team FRONTEND (3 tasks, ~1-2h)

| # | Task | File | Est. |
|---|------|------|------|
| F1 | Add `transcribeVideo()` to `api.js` with 30s timeout + add to default export | `services/api.js` | 15min |
| F2 | Replace mock in `TranscricaoPage.jsx`: delete `MOCK_TRANSCRIPTION`, use `transcribeVideo` API call, map error codes to user messages, update TipBox text | `TranscricaoPage.jsx` | 30min |
| F3 | Replace mock validation in `YouTubeInput.jsx` with YouTube oembed call; update `ProgressOverlay.jsx` messages | `YouTubeInput.jsx`, `ProgressOverlay.jsx` | 30min |

### Execution Order
1. **B1** → **B2** → **B3** (sequential — each depends on previous)
2. **F1** → **F2** + **F3** (F2 and F3 can be parallel after F1)
3. Backend and Frontend can be developed in **parallel** — frontend can test against mock API while backend is built

---

## 8. Testing Checklist

### Backend Tests
- [ ] `extract_video_id` handles all 4 URL formats + invalid URLs
- [ ] `get_video_metadata` returns correct shape for valid video
- [ ] `get_video_metadata` raises `VideoNotFoundError` for invalid/private video
- [ ] `get_captions` returns merged segments with correct time formatting
- [ ] `get_captions` raises `CaptionsNotAvailableError` for videos without captions
- [ ] `_merge_segments` produces segments of ~30-60s from fine-grained fragments
- [ ] `_merge_segments` handles edge cases: single fragment, very long video, empty input
- [ ] `transcribe_handler` returns 400 for invalid URL
- [ ] `transcribe_handler` returns 404 for non-existent video
- [ ] `transcribe_handler` returns 422 for video without captions
- [ ] `transcribe_handler` returns 200 with correct schema for valid video with captions
- [ ] Rate limiter blocks after 10 requests in 60 seconds

### Frontend Tests
- [ ] `transcribeVideo` API function calls correct endpoint with correct body
- [ ] `YouTubeInput` shows green check for valid video via oembed
- [ ] `YouTubeInput` shows error for private/non-existent video
- [ ] `TranscricaoPage` navigates to `/criar/texto-base` after successful transcription
- [ ] `TranscricaoPage` shows error banner for 422 (no captions)
- [ ] `TranscricaoPage` shows error banner for 404 (video not found)
- [ ] `TranscricaoPage` shows error banner for 429 (rate limited)
- [ ] Cancel button stops the request (AbortController)
- [ ] Progress bar animates smoothly during API call

### Integration Tests
- [ ] Full flow: paste URL → validate → transcribe → lands on texto-base with data
- [ ] Video without captions shows clear error message, user can try another URL
- [ ] Transcription data in texto-base matches expected segment structure

---

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `youtube-transcript-api` breaks (YouTube changes internal API) | Feature down | Medium (has happened before) | Pin version, monitor GitHub issues, have fallback error message |
| Video has only auto-generated captions with poor quality | Bad UX | Medium | Show `metadata.caption_type` in UI so user knows quality level |
| YouTube rate-limits our server IP | Feature down temporarily | Low (caption endpoint is lightweight) | Implement exponential backoff in `youtube_service.py`, per-user rate limiting on our end |
| Very long videos (3+ hours) produce too many segments | Slow response, large payload | Low | Cap at 200 segments, warn user if truncated |
| Video has captions only in unsupported language | User confusion | Low | Return 422 with clear message listing which languages we support |

---

## 10. Future Enhancements (Not in scope)

- **Topic extraction per segment** — call Claude Haiku to assign `topic` field to each segment
- **Speaker detection from captions** — some YouTube captions include speaker labels
- **Whisper fallback** — if no captions available, offer audio transcription (requires ffmpeg + Whisper API)
- **Caching** — cache transcription results by video ID (TTL 24h) to avoid redundant YouTube calls
- **Playlist support** — allow pasting a playlist URL and selecting individual videos
