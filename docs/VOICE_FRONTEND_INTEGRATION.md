# Voice Frontend Integration Guide

This document describes how the frontend should integrate with the current backend voice feature.

Current implementation status:
- Transport: WebSocket
- Input mode: transcript-first
- TTS: ElevenLabs (with backend stub fallback when API key is missing)
- Server-side STT: not implemented in this phase

## 1. Endpoint

Base API prefix is `/api/v1`.

WebSocket URL:
- `ws://<host>/api/v1/voice/ws/{conversation_id}`

Example:
- `ws://localhost:8000/api/v1/voice/ws/3e4e2aa9-5fd2-4b96-b0d4-880ebf9c44ef`

## 2. Authentication

A valid JWT is required.

Supported auth modes:
1. Header (preferred)
- `Authorization: Bearer <jwt>`

2. Query param fallback
- `?token=<jwt>`

If auth fails or conversation ownership fails, the socket is closed with policy violation.

## 3. High-level Turn Flow

1. Frontend opens socket to conversation URL.
2. Backend sends `session.ready`.
3. Frontend sends `input_text.final` with transcript text.
4. Backend streams:
- `assistant.text.delta` events (token-like text chunks)
- `assistant.text.done` (full text)
- `output_audio.chunk` (base64 audio bytes)
- `output_audio.done` (chunk count)
- `turn.done` (turn completion payload)

Messages are persisted by backend as user + assistant text messages in the conversation.

## 4. Client-to-Server Events

Envelope:
```json
{
  "type": "<event_type>",
  "data": {}
}
```

Supported client `type` values:
- `input_text.final`
- `input_audio.append`
- `input_audio.commit`
- `turn.cancel`
- `ping`

### 4.1 input_text.final
Primary supported input for this phase.

```json
{
  "type": "input_text.final",
  "data": {
    "text": "I feel overwhelmed today"
  }
}
```

Validation:
- `text` min length: 1
- `text` max length: 32000

### 4.2 input_audio.append and input_audio.commit
Accepted by schema but not implemented server-side in this phase.
Sending these returns an `error` event with code `stt_not_implemented`.

### 4.3 turn.cancel
Current behavior returns immediate `turn.done` with:
```json
{
  "type": "turn.done",
  "data": {
    "cancelled": true
  }
}
```

### 4.4 ping
Server responds with `pong`.

## 5. Server-to-Client Events

Envelope:
```json
{
  "type": "<event_type>",
  "data": {},
  "ts": "2026-03-31T10:15:00.123456+00:00"
}
```

Supported server `type` values:
- `session.ready`
- `assistant.text.delta`
- `assistant.text.done`
- `output_audio.chunk`
- `output_audio.done`
- `turn.done`
- `error`
- `pong`

### 5.1 session.ready
Sent after successful auth and conversation access checks.

```json
{
  "type": "session.ready",
  "data": {
    "conversation_id": "3e4e2aa9-5fd2-4b96-b0d4-880ebf9c44ef"
  },
  "ts": "..."
}
```

### 5.2 assistant.text.delta
Incremental assistant text chunks.

```json
{
  "type": "assistant.text.delta",
  "data": {
    "text": "I hear you "
  },
  "ts": "..."
}
```

### 5.3 assistant.text.done
Final complete assistant text.

```json
{
  "type": "assistant.text.done",
  "data": {
    "text": "I hear you, and what you're feeling is valid..."
  },
  "ts": "..."
}
```

### 5.4 output_audio.chunk
Audio bytes for playback, base64 encoded.

```json
{
  "type": "output_audio.chunk",
  "data": {
    "audio_b64": "<base64 audio chunk>"
  },
  "ts": "..."
}
```

### 5.5 output_audio.done
Signals end of streamed audio for this turn.

```json
{
  "type": "output_audio.done",
  "data": {
    "chunks": 14
  },
  "ts": "..."
}
```

### 5.6 turn.done
Final turn completion event.

Normal completion:
```json
{
  "type": "turn.done",
  "data": {
    "assistant_text": "I hear you, and what you're feeling is valid..."
  },
  "ts": "..."
}
```

Cancel completion:
```json
{
  "type": "turn.done",
  "data": {
    "cancelled": true
  },
  "ts": "..."
}
```

### 5.7 error
Possible error payloads include:

1. STT not implemented
```json
{
  "type": "error",
  "data": {
    "code": "stt_not_implemented",
    "message": "Server-side STT is not implemented in this phase. Send input_text.final."
  },
  "ts": "..."
}
```

2. Unsupported event
```json
{
  "type": "error",
  "data": {
    "code": "unsupported_event",
    "message": "Unsupported event type: <...>"
  },
  "ts": "..."
}
```

3. Generic stream failure
```json
{
  "type": "error",
  "data": {
    "code": "voice_stream_failed",
    "message": "Voice stream failed."
  },
  "ts": "..."
}
```

## 6. Frontend Playback Guidance

Recommended handling for `output_audio.chunk`:
1. Decode `audio_b64` into bytes.
2. Append to an in-memory queue.
3. Feed queue to your audio pipeline in order.
4. Stop playback when `output_audio.done` is received and queue is drained.

Notes:
- Audio format depends on backend voice output setting and provider response.
- Keep frontend decoder tolerant to chunk boundaries.

## 7. Suggested Frontend State Machine

Minimal state flags:
- `socketConnected`
- `sessionReady`
- `isGeneratingText`
- `isStreamingAudio`
- `isTurnComplete`
- `lastError`

Suggested transitions:
1. On open -> wait for `session.ready`
2. On `session.ready` -> allow send
3. On send `input_text.final` -> set generating state
4. On `assistant.text.delta` -> append UI text
5. On `assistant.text.done` -> freeze final text
6. On `output_audio.chunk` -> enqueue/play audio
7. On `output_audio.done` -> mark audio stream complete
8. On `turn.done` -> mark turn complete and idle
9. On `error` -> show recoverable error and keep socket unless closed

## 8. Example Browser Integration (TypeScript)

```ts
type VoiceClientEvent = {
  type: "input_text.final" | "input_audio.append" | "input_audio.commit" | "turn.cancel" | "ping";
  data: Record<string, unknown>;
};

type VoiceServerEvent = {
  type:
    | "session.ready"
    | "assistant.text.delta"
    | "assistant.text.done"
    | "output_audio.chunk"
    | "output_audio.done"
    | "turn.done"
    | "error"
    | "pong";
  data: Record<string, unknown>;
  ts: string;
};

export function connectVoiceSocket(baseWsUrl: string, conversationId: string, jwt: string) {
  const ws = new WebSocket(`${baseWsUrl}/api/v1/voice/ws/${conversationId}?token=${encodeURIComponent(jwt)}`);

  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data) as VoiceServerEvent;

    switch (msg.type) {
      case "session.ready":
        break;
      case "assistant.text.delta":
        // append partial text
        break;
      case "assistant.text.done":
        // set final assistant text
        break;
      case "output_audio.chunk": {
        const b64 = String(msg.data.audio_b64 ?? "");
        // decode + queue for playback
        break;
      }
      case "output_audio.done":
        break;
      case "turn.done":
        break;
      case "error":
        // show msg.data.code + msg.data.message
        break;
      case "pong":
        break;
    }
  };

  const sendFinalTranscript = (text: string) => {
    const payload: VoiceClientEvent = { type: "input_text.final", data: { text } };
    ws.send(JSON.stringify(payload));
  };

  const ping = () => ws.send(JSON.stringify({ type: "ping", data: {} } satisfies VoiceClientEvent));
  const cancel = () => ws.send(JSON.stringify({ type: "turn.cancel", data: {} } satisfies VoiceClientEvent));

  return { ws, sendFinalTranscript, ping, cancel };
}
```

## 9. Known Limits for Frontend Team

1. Transcript-first only
- Frontend must send `input_text.final` for real turn execution.

2. Audio input events are future-compatible only
- `input_audio.append` and `input_audio.commit` currently return `stt_not_implemented`.

3. No server-side resume token yet
- Reconnect should be treated as a fresh realtime session.

## 10. Integration Checklist

- Open WebSocket with valid JWT.
- Wait for `session.ready` before sending user input.
- Send `input_text.final` with transcript text.
- Render text from `assistant.text.delta` and finalize on `assistant.text.done`.
- Decode and play audio from `output_audio.chunk` until `output_audio.done`.
- End turn on `turn.done`.
- Handle `error` gracefully and allow retry.
