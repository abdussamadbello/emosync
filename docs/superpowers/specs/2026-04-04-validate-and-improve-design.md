# EmoSync Validation & Improvement Spec

**Date:** 2026-04-04
**Scope:** Security hardening, feature fixes, data flow corrections, frontend hardening, test coverage
**Approach:** Surgical Hardening (Approach A) — fix in-place with minimal structural changes

---

## Phase 1: Backend Security & Stability

### 1.1 JWT Secret Startup Validation
**File:** `backend/app/core/config.py`
**Issue:** Default `jwt_secret = "change-me-in-production"` allows token forgery.
**Fix:** Add `@model_validator(mode="after")` that rejects the default unless `database_url` points to localhost. Fail at import time, before any request is served.

### 1.2 Voice Handler Transaction Fix
**File:** `backend/app/api/v1/voice.py:119-152`
**Issue:** User message committed before assistant response streams. Orphaned messages on failure.
**Fix:** Defer user message commit. Accumulate assistant text fully, then save both in a single `session.begin()` transaction. Also wrap `base64.b64decode()` at line 88 in try/except for `binascii.Error`.

### 1.3 LLM Call Timeouts
**Files:** `backend/app/agent/nodes/historian.py:136`, `specialist.py:63`, `anchor.py:59`
**Issue:** `llm.ainvoke()` has no timeout — hung Gemini API blocks forever.
**Fix:** Wrap each in `asyncio.wait_for(..., timeout=30.0)`. Catch `asyncio.TimeoutError` separately from generic `Exception`.

### 1.4 Historian JSON Parsing Fix
**File:** `backend/app/agent/nodes/historian.py:139-160`
**Issues:**
- Markdown fence extraction splits on ` ``` ` which breaks with multiple code blocks
- `"response" in dir()` is unreliable for scope check
- Unused `import numpy as np` and duplicate `import json as js`
**Fix:**
- Use `content.split("```json", 1)[1].split("```", 1)[0]` for safe extraction
- Initialize `response_content = None` before try block, use in except
- Remove unused imports, consolidate to single `json` and `os` imports

### 1.5 CORS Restriction
**File:** `backend/app/main.py:29-30`
**Issue:** `allow_methods=["*"]` and `allow_headers=["*"]` with credentials enabled.
**Fix:** Restrict to `["GET", "POST", "OPTIONS"]` and `["Content-Type", "Authorization", "X-Request-ID"]`.

### 1.6 Rate Limiting on Auth
**File:** `backend/app/api/v1/auth.py`
**Issue:** No rate limiting — brute-force trivial.
**Fix:** Add `slowapi` dependency. Apply `5/minute` per IP on `/login`, `3/minute` on `/register`.

---

## Phase 2: Backend Feature Fixes

### 2.1 Real Cosine Similarity in Historian
**File:** `backend/app/agent/nodes/historian.py:39-53`
**Issue:** `retrieve_relevant_chunks()` creates a dummy zero-vector and returns first top_k chunks regardless of relevance. Meanwhile `retrieve_journal_context()` (line 106-111) uses proper cosine similarity but crashes if `vector_store.json` is missing.
**Fix:** Refactor `retrieve_relevant_chunks()` to:
- Use `Embedder` for query embedding + `VectorRetriever.search()` for cosine similarity
- Handle missing `vector_store.json` gracefully (return empty, log warning once)
- Make it `async` since `Embedder.embed()` is async
- Remove the separate `retrieve_journal_context()` or unify both paths

### 2.2 Specific Exception Handling in Agent Nodes
**Files:** `historian.py`, `specialist.py`, `anchor.py`
**Issue:** All catch bare `Exception` — API down, timeout, parse error all look the same.
**Fix:** Catch in order: `asyncio.TimeoutError`, `ValueError`/`json.JSONDecodeError`, then `Exception`. Same fallback text, but actionable logs.

### 2.3 SSE Error Categorization
**File:** `backend/app/api/v1/chat.py:151-155`
**Issue:** All exceptions yield `"stream_failed"`. Clients can't distinguish timeout from internal error.
**Fix:** Catch `asyncio.TimeoutError` → `"timeout"`, `HTTPException` → forward detail, `Exception` → `"internal_error"`.

### 2.4 Clean Up Unused Imports
**File:** `backend/app/agent/nodes/historian.py`
**Fix:** Remove `numpy`, `json as js`, consolidate imports. Keep `Embedder`/`VectorRetriever` for refactored retrieval.

---

## Phase 3: Data Flow Fixes (from end-to-end trace)

### 3.1 Missing `user.transcript` Event (CRITICAL)
**Files:** `backend/app/schemas/voice.py`, `backend/app/api/v1/voice.py`
**Issue:** Frontend expects `"user.transcript"` server event after STT, but backend never sends it. User's spoken words are invisible in chat — the "…" placeholder is never replaced with real text.
**Fix:**
- Add `"user.transcript"` to `ServerEventType` literal in `schemas/voice.py`
- After successful transcription in `voice.py` (after line 99/108), send: `await websocket.send_json(VoiceServerEvent(type="user.transcript", data={"text": transcript}).model_dump())`

### 3.2 AudioBuffer Overflow Error Handling
**Files:** `backend/app/services/audio/buffer.py`, `backend/app/api/v1/voice.py`
**Issue:** `AudioBuffer.append()` raises `ValueError` on overflow. Not caught specifically — falls through to generic error. Frontend tries to play empty fallback TTS.
**Fix:** Catch `ValueError` from `audio_buffer.append()` in voice.py, send a specific error event `{"code": "audio_buffer_overflow", "message": "Audio too long. Please try a shorter message."}`, then `audio_buffer.reset()`.

### 3.3 VectorRetriever FileNotFoundError
**File:** `backend/app/ingestion/vector_retriever.py:5-7`
**Issue:** `__init__` opens file immediately — `FileNotFoundError` if missing. Caller (`historian_node`) catches it as generic `Exception`, entire historian produces empty context with unclear log.
**Fix:** Wrap file open in try/except in `VectorRetriever.__init__`, set `self.store = []` if missing, log clear warning. Also add guard in `retrieve_relevant_chunks()`.

---

## Phase 4: Frontend Hardening

### 4.1 JWT Token Exposure in WebSocket URL
**File:** `frontend/hooks/use_voice_chat.ts:486`
**Issue:** Token passed as `?token=...` query param — leaks to browser history, logs, referrer headers.
**Fix:** Connect without token in URL. Send token as first message after `ws.onopen`: `{type: "auth", data: {token}}`. Update backend `_resolve_socket_user()` to accept token from first WS message. Keep query-param path for backward compat during migration.

### 4.2 Race Condition on Rapid Message Sends
**File:** `frontend/components/chat_view.tsx:269-271`
**Issue:** `setIsTyping(true)` is async — double-clicks sneak through.
**Fix:** Add `useRef<boolean>(false)` as `is_sending_ref`. Set synchronously at top of `handle_send`, check before proceeding.

### 4.3 SSE Stream Hang Recovery
**File:** `frontend/components/chat_view.tsx:307-330`
**Issue:** If backend never sends "done" event, UI stuck in typing state forever.
**Fix:** Add 60-second timeout using `AbortController` + `setTimeout`. Add `finally` block to guarantee `setIsTyping(false)`.

### 4.4 Token Expiry Handling
**File:** `frontend/lib/api.ts`
**Issue:** No token refresh mechanism. 401 responses silently fail.
**Fix:** Add wrapper that intercepts 401 responses, clears auth, redirects to `/auth/login?expired=1`. Login page shows "Session expired" when param present.

### 4.5 Conversation List Staleness
**File:** `frontend/components/chat_view.tsx:201-205`
**Issue:** Sidebar only refreshes on "done" SSE events.
**Fix:** Also call `load_conversations` after `create_conversation`. Add 30s poll while tab visible via `document.visibilityState`.

### 4.6 Voice Chat Cleanup & Memory
**File:** `frontend/hooks/use_voice_chat.ts`
**Issues:** Unbounded audio_chunks_ref growth; state-update-after-unmount on disconnect.
**Fix:** Cap `audio_chunks_ref` total size. Add `is_mounted_ref` guard to prevent post-unmount state updates.

### 4.7 Silent Error Swallowing
**File:** `frontend/components/chat_view.tsx` (multiple catch blocks)
**Issue:** Empty `catch {}` blocks hide failures.
**Fix:** Add `console.error` in all catch blocks. Show toast/inline error for user-facing failures.

### 4.8 Accessibility & Polish
**Files:** `frontend/components/chat_view.tsx`, `frontend/hooks/use_voice_chat.ts`
**Fix:**
- Add `aria-label` to mic, send, sidebar toggle buttons
- Remove ~20 `console.log` statements from voice chat hook
- Add loading skeleton during `is_session_loading`

---

## Phase 5: Test Coverage

### 5.1 `test_voice_edges.py`
- Invalid base64 audio → error event, not crash
- Empty audio commit → `"empty_audio"` error
- Disconnect mid-stream → clean shutdown
- Conversation ownership violation → close 1008
- `user.transcript` event sent after STT

### 5.2 `test_historian_parsing.py`
- Valid JSON response → parsed correctly
- JSON in markdown fences → extracted
- Multiple code blocks → first JSON block extracted
- Non-JSON response → raw text fallback
- Missing vector_store.json → empty context, no crash

### 5.3 `test_agent_errors.py`
- Specialist timeout → fallback response
- Anchor failure → specialist response passed through
- Full pipeline with no API key → stub response

### 5.4 `test_auth_ratelimit.py`
- 5 rapid login attempts → normal responses
- 6th attempt → HTTP 429

---

## Out of Scope
- Email verification for registration
- Distributed tracing / OpenTelemetry
- Load testing
- Frontend component refactoring / naming standardization
- Multi-region deployment
