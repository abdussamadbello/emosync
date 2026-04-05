# Voice Frontend Integration Guide

This document describes the current voice transport between the frontend and backend.

## Current status

- Transport: WebSocket
- Default provider: Gemini Live
- Input format: raw PCM, 16-bit little-endian, base64 over JSON
- Output format: raw PCM, 16-bit little-endian, base64 over JSON
- Legacy fallback: the backend can still advertise `provider: "legacy"` when Gemini Live is unavailable

## Endpoint

- `ws://<host>/api/v1/voice/ws/{conversation_id}`

Example:
- `ws://localhost:8000/api/v1/voice/ws/3e4e2aa9-5fd2-4b96-b0d4-880ebf9c44ef`

## Authentication

The socket requires a valid JWT.

Supported auth modes:
1. First-frame auth message:
```json
{
  "type": "auth",
  "data": { "token": "<jwt>" }
}
```
2. Legacy header/query-param auth is still accepted by the backend.

## Session-ready metadata

After auth and conversation checks, the backend sends:

```json
{
  "type": "session.ready",
  "data": {
    "conversation_id": "<uuid>",
    "provider": "gemini_live",
    "model": "gemini-2.5-flash-native-audio-preview-12-2025",
    "input_audio_format": "pcm_s16le",
    "input_sample_rate_hz": 16000,
    "output_audio_format": "pcm_s16le",
    "output_sample_rate_hz": 24000
  },
  "ts": "..."
}
```

If the backend falls back, `provider` is `legacy`.

## High-level flow

1. Frontend opens the socket and sends the auth message.
2. Backend replies with `session.ready`.
3. Frontend starts microphone capture.
4. Frontend streams PCM chunks with `input_audio.append`.
5. Frontend sends `input_audio.commit` after local silence to flush the current turn.
6. Backend relays Gemini Live transcriptions and audio back to the client.
7. Backend persists the final user transcript and assistant text when `turn.done` is emitted.

## Client events

Envelope:

```json
{
  "type": "<event_type>",
  "data": {}
}
```

Supported client `type` values:
- `input_audio.append`
- `input_audio.commit`
- `input_audio.clear`
- `input_text.final`
- `turn.cancel`
- `ping`

### `input_audio.append`

Gemini Live path:

```json
{
  "type": "input_audio.append",
  "data": {
    "audio": "<base64 pcm bytes>",
    "mime_type": "audio/pcm;rate=16000"
  }
}
```

### `input_audio.commit`

Signals end-of-stream for the current captured utterance.

```json
{
  "type": "input_audio.commit",
  "data": {
    "mime_type": "audio/pcm;rate=16000"
  }
}
```

### `input_text.final`

Optional text-only fallback:

```json
{
  "type": "input_text.final",
  "data": {
    "text": "I feel overwhelmed today"
  }
}
```

### `turn.cancel`

Returns:

```json
{
  "type": "turn.done",
  "data": {
    "cancelled": true
  }
}
```

### `ping`

Returns `pong`.

## Server events

Supported server `type` values:
- `session.ready`
- `user.transcript`
- `assistant.text.delta`
- `assistant.text.done`
- `output_audio.chunk`
- `output_audio.done`
- `turn.interrupted`
- `turn.done`
- `error`
- `pong`

### `user.transcript`

Incremental or final user transcript:

```json
{
  "type": "user.transcript",
  "data": {
    "text": "I feel overwhelmed today"
  },
  "ts": "..."
}
```

### `assistant.text.delta`

Incremental assistant text from Gemini Live output transcription:

```json
{
  "type": "assistant.text.delta",
  "data": {
    "text": "I hear you"
  },
  "ts": "..."
}
```

### `output_audio.chunk`

Realtime PCM audio chunk:

```json
{
  "type": "output_audio.chunk",
  "data": {
    "audio_b64": "<base64 pcm bytes>",
    "mime_type": "audio/pcm;rate=24000",
    "sample_rate_hz": 24000
  },
  "ts": "..."
}
```

### `turn.interrupted`

Emitted when Gemini Live cancels an in-flight response because the user interrupted.

### `turn.done`

Final turn completion:

```json
{
  "type": "turn.done",
  "data": {
    "assistant_text": "I hear you, and what you're feeling makes sense."
  },
  "ts": "..."
}
```

## Frontend notes

- Prefer the backend-advertised provider instead of assuming Gemini Live is always available.
- When `provider === "gemini_live"`, the frontend should capture PCM instead of using browser speech recognition.
- Stop local playback immediately when `turn.interrupted` arrives.
- Preserve browser `speechSynthesis` only as a last-resort fallback when no audio chunks are received.
