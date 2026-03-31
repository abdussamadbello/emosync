# Backend Voice Architecture

This reference is for implementing EmoSync's backend voice stack without fighting the current codebase.

## Baseline assumption

Text chat already works through:

- `POST /api/v1/conversations/{id}/messages/stream`
- `run_turn()` in `backend/app/services/chat_turn.py`
- SSE token streaming

Voice should be additive, not a rewrite.

## Recommended route strategy

Prefer a separate authenticated WebSocket endpoint, for example:

- `GET /api/v1/voice/ws`
- or `GET /api/v1/conversations/{id}/voice/ws`

Use WebSockets for bidirectional low-latency voice events. Keep SSE for text-only chat.

## Recommended event model

Client -> server:

- `session.start`
- `input_audio.append`
- `input_audio.commit`
- `input_audio.cancel`
- `response.cancel`
- `ping`

Server -> client:

- `session.ready`
- `transcript.partial`
- `transcript.final`
- `assistant.text.delta`
- `assistant.text.done`
- `output_audio.chunk`
- `output_audio.done`
- `turn.done`
- `error`

Use monotonic `sequence` values on audio-related events.

## Buffering guidance

For audio buffering, prefer an explicit buffer object rather than raw lists in the route.

Suggested responsibilities:

- accept chunks with sequence numbers
- reject duplicates or out-of-order chunks when strict ordering is required
- expose byte length and duration estimates
- support `flush()` into a completed frame or temporary file
- support `reset()` on cancellation or turn completion

Keep codec conversion separate from the buffer object.

## Provider boundaries

Prefer small interfaces:

```python
class SpeechToTextService(Protocol):
    async def transcribe(self, audio: bytes, *, mime_type: str) -> str: ...


class TextToSpeechService(Protocol):
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]: ...
```

Concrete adapters can live behind them:

- `WhisperSpeechToTextService`
- `ElevenLabsTextToSpeechService`
- `StubSpeechToTextService`
- `StubTextToSpeechService`

## Session orchestration

A voice session manager should own:

- WebSocket connection
- authenticated user identity
- active conversation id
- input buffer
- current assistant task
- current TTS task
- cancellation tokens

This should be a service object, not a route-global dict of loose values.

## Integration with `run_turn()`

Default flow:

1. collect audio chunks
2. transcribe into user text
3. pass text into `run_turn()`
4. emit assistant text deltas to client
5. pass completed text into TTS
6. stream synthesized audio back to client

This keeps text and voice aligned with one backend reasoning path.

## Failure handling

Prefer graceful degradation:

- if STT fails, emit `error` and keep socket open if recovery is possible
- if `run_turn()` fails, emit a safe fallback text event
- if TTS fails, still deliver text completion if available
- if provider keys are missing in local dev, use deterministic stubs

## Testing targets

Add tests for:

- chunk ordering and buffer reset
- session start and cleanup
- transcript -> assistant -> audio event ordering
- cancellation during STT, agent generation, and TTS
- missing API key fallback behavior

Avoid live provider calls in tests.
