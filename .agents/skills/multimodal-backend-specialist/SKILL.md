---
name: multimodal-backend-specialist
description: Backend specialist for EmoSync voice features. Use when implementing or refactoring FastAPI audio pipelines, Whisper-style speech-to-text, ElevenLabs text-to-speech, WebSocket session handling, audio buffering, turn synchronization, or real-time streaming beside the existing SSE chat path.
---

# Multimodal Backend Specialist

Use this skill for backend-only multimodal work in EmoSync.

The current backend already has:

- FastAPI app setup in `backend/app/main.py`
- Authenticated chat routes in `backend/app/api/v1/chat.py`
- A single text-response boundary in `backend/app/services/chat_turn.py`
- SSE token streaming for text responses

The current backend does not yet have:

- Voice session routes
- Audio buffering/session state
- Whisper/STT adapters
- ElevenLabs/TTS adapters
- Real-time duplex coordination between audio input, agent turns, and audio output

## Goals

Implement multimodal support in a way that fits the current backend instead of replacing it.

- Keep `run_turn()` as the text-generation boundary unless the task explicitly requires a new multimodal boundary.
- Add voice-specific orchestration around the existing chat pipeline.
- Prefer provider abstractions so Whisper and ElevenLabs are swappable and easy to stub in tests.
- Keep transport concerns, provider SDK logic, and session state in separate modules.
- Preserve async behavior end to end.

## Preferred backend shape

When adding voice support, prefer this split:

- `app/api/v1/voice.py`: WebSocket or voice-session HTTP endpoints
- `app/services/realtime/`: session orchestration, turn coordination, event emission
- `app/services/audio/`: buffers, chunk assembly, transcoding helpers, VAD hooks if needed
- `app/services/stt/`: speech-to-text interface plus provider adapters
- `app/services/tts/`: text-to-speech interface plus ElevenLabs adapter

Do not bury provider calls directly in route handlers.

## Workflow

1. Read the current backend boundary first.
   Inspect `backend/app/main.py`, `backend/app/api/v1/chat.py`, `backend/app/api/deps.py`, and `backend/app/services/chat_turn.py`.

2. Decide whether the task belongs beside SSE or replaces it.
   Default: add a dedicated voice route and keep text SSE unchanged.

3. Add config before implementation.
   Extend `backend/app/core/config.py` and `.env.example` with only the variables needed by the chosen providers.

4. Create provider interfaces before SDK-specific code.
   Use small protocols or service classes such as `SpeechToTextService` and `TextToSpeechService`.

5. Add session state and buffering.
   Introduce a per-connection session object that tracks:
   - `session_id`
   - authenticated user
   - input audio sequence numbers
   - accumulated PCM or encoded chunks
   - current turn status
   - cancellation/interruption flags
   - outgoing audio/text event ordering

6. Define an explicit event contract.
   The frontend should not infer backend state from timing alone. Use typed events for connect, partial transcript, final transcript, assistant text, audio chunk, turn done, and error.

7. Keep turn orchestration linear and cancel-safe.
   User audio in -> buffer/assemble -> STT -> `run_turn()` -> TTS -> streamed audio out.
   If interruption is supported, make cancellation explicit and idempotent.

8. Test with fakes, not live providers.
   Unit tests should cover buffering, event ordering, cancellation, and fallback behavior without real network calls.

## Project-specific rules

- Reuse existing auth patterns from `backend/app/api/deps.py`.
- Keep JSON error semantics aligned with the rest of the API.
- Do not couple ElevenLabs output generation to database writes.
- Do not force WebSockets into text chat routes that already work with SSE.
- Keep local dev viable when provider API keys are absent by using deterministic stubs.
- Avoid blocking calls in WebSocket handlers; offload provider I/O through async clients or thread-safe wrappers.

## Recommended implementation order

1. Add config and provider interfaces.
2. Add audio buffer/session primitives.
3. Add a WebSocket route with authentication and a minimal event contract.
4. Wire STT input flow.
5. Reuse `run_turn()` for assistant text generation.
6. Add ElevenLabs TTS streaming.
7. Add interruption, cancellation, and timeout handling.
8. Add tests for session lifecycle and event sequencing.

## When to read more

- For concrete architecture guidance, module layout, and event names, read `references/backend-voice-architecture.md`.

