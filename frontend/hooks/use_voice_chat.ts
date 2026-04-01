"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { use_speech_recognition } from "@/hooks/use_speech_recognition";

const WS_BASE =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
    /^http/,
    "ws"
  );

export type VoiceChatStatus =
  | "disconnected"
  | "connecting"
  | "listening"
  | "processing"
  | "speaking"
  | "error";

interface UseVoiceChatOptions {
  /** Called when STT finalises a user utterance (add it to your message list). */
  on_user_transcript: (text: string) => void;
  /** Called when the full assistant turn is complete (text + audio done). */
  on_assistant_message: (text: string) => void;
  /** Called incrementally as the assistant text streams in. */
  on_assistant_delta: (delta: string) => void;
  /** Called with an error string when the session fails unrecoverably. */
  on_error?: (msg: string) => void;
}

interface UseVoiceChatReturn {
  status: VoiceChatStatus;
  /** Streams in the current assistant reply word-by-word. Reset on each turn. */
  streaming_text: string;
  is_stt_supported: boolean;
  interim_transcript: string;
  /**
   * Opens the voice WebSocket for the given conversation and starts listening.
   * Creates a new conversation automatically if conversation_id is null.
   */
  connect: (conversation_id: string, token: string) => Promise<void>;
  /** Closes the WebSocket, cancels audio, and stops the mic. */
  disconnect: () => void;
}

/**
 * Manages the full voice-to-voice loop:
 *   Web Speech API STT → backend WebSocket agent → ElevenLabs TTS (AudioContext)
 *
 * Text is buffered silently during the agent turn, then revealed word-by-word
 * in sync with the audio playback so the user sees + hears the response at the
 * same pace.  The mic is killed during processing/playback to prevent it from
 * picking up the assistant's spoken output.
 */
export function use_voice_chat({
  on_user_transcript,
  on_assistant_message,
  on_assistant_delta,
  on_error,
}: UseVoiceChatOptions): UseVoiceChatReturn {
  const [status, setStatus] = useState<VoiceChatStatus>("disconnected");
  const [streaming_text, setStreamingText] = useState("");

  const ws_ref = useRef<WebSocket | null>(null);
  const audio_chunks_ref = useRef<string[]>([]);
  const full_text_ref = useRef("");
  const is_busy_ref = useRef(false);
  const reveal_timer_ref = useRef<number | null>(null);

  // Stable refs so callbacks set after mount see the latest versions.
  const on_user_transcript_ref = useRef(on_user_transcript);
  const on_assistant_message_ref = useRef(on_assistant_message);
  const on_assistant_delta_ref = useRef(on_assistant_delta);
  const on_error_ref = useRef(on_error);
  useEffect(() => { on_user_transcript_ref.current = on_user_transcript; }, [on_user_transcript]);
  useEffect(() => { on_assistant_message_ref.current = on_assistant_message; }, [on_assistant_message]);
  useEffect(() => { on_assistant_delta_ref.current = on_assistant_delta; }, [on_assistant_delta]);
  useEffect(() => { on_error_ref.current = on_error; }, [on_error]);

  const start_stt_ref = useRef<() => void>(() => {});
  const stop_stt_ref = useRef<() => void>(() => {});

  // ── Text reveal ────────────────────────────────────────────────────────────
  // These only touch refs, so they are render-stable and safe to call from
  // any useCallback without adding them to dependency arrays.

  /**
   * Cancels any in-flight word-by-word reveal timer.
   */
  function clear_reveal_timer() {
    if (reveal_timer_ref.current !== null) {
      window.clearInterval(reveal_timer_ref.current);
      reveal_timer_ref.current = null;
    }
  }

  /**
   * Splits text into words and feeds them to on_assistant_delta one at a time,
   * spaced evenly over duration_ms so the text appears in sync with audio.
   */
  function start_text_reveal(text: string, duration_ms: number) {
    clear_reveal_timer();
    const words = text.split(/\s+/).filter(Boolean);
    if (words.length === 0) return;
    const interval_ms = Math.max(duration_ms / words.length, 30);
    let idx = 0;
    reveal_timer_ref.current = window.setInterval(() => {
      if (idx < words.length) {
        const word = (idx === 0 ? "" : " ") + words[idx];
        on_assistant_delta_ref.current(word);
        setStreamingText((prev) => prev + word);
        idx++;
      } else {
        clear_reveal_timer();
      }
    }, interval_ms);
  }

  // ── Audio playback ──────────────────────────────────────────────────────────

  /**
   * Called when audio playback finishes (ElevenLabs or fallback).
   * Clears busy state, stops any remaining text reveal, and restarts the mic.
   */
  const on_audio_ended = useCallback(() => {
    clear_reveal_timer();
    is_busy_ref.current = false;
    setStatus("listening");
    start_stt_ref.current();
  }, []);

  /**
   * Decodes buffered base64 audio chunks, plays them via AudioContext, and
   * kicks off a synchronised word-by-word text reveal over the audio duration.
   */
  const play_audio = useCallback(
    async (fallback_text: string) => {
      const chunks = audio_chunks_ref.current;
      const text = full_text_ref.current;

      if (chunks.length === 0) {
        const word_count = text.split(/\s+/).filter(Boolean).length;
        start_text_reveal(text, Math.max(word_count * 120, 500));
        speak_fallback(fallback_text, on_audio_ended);
        return;
      }

      const byte_arrays = chunks.map((b64) => {
        const binary = atob(b64);
        const arr = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) arr[i] = binary.charCodeAt(i);
        return arr;
      });
      const total = byte_arrays.reduce((sum, a) => sum + a.length, 0);
      const bytes = new Uint8Array(total);
      let offset = 0;
      for (const arr of byte_arrays) { bytes.set(arr, offset); offset += arr.length; }

      try {
        const ctx = new AudioContext();
        const buf = await ctx.decodeAudioData(bytes.buffer);
        const src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(ctx.destination);
        src.onended = on_audio_ended;
        src.start(0);
        start_text_reveal(text, buf.duration * 1000);
        console.log("[Voice] ElevenLabs playing —", buf.duration.toFixed(2), "s");
      } catch (err) {
        console.error("[Voice] AudioContext error:", err);
        const word_count = text.split(/\s+/).filter(Boolean).length;
        start_text_reveal(text, Math.max(word_count * 120, 500));
        speak_fallback(fallback_text, on_audio_ended);
      }
    },
    [on_audio_ended]
  );

  // ── Send transcript ─────────────────────────────────────────────────────────

  /**
   * Sends the finalised STT transcript to the backend and immediately kills the
   * mic so it does not pick up the assistant's spoken reply.
   */
  const send_transcript = useCallback((text: string) => {
    if (ws_ref.current?.readyState !== WebSocket.OPEN) return;
    if (is_busy_ref.current) {
      console.warn("[Voice] pipeline busy — dropping transcript:", text);
      return;
    }
    console.log("[Voice] → sending transcript:", text);
    is_busy_ref.current = true;
    stop_stt_ref.current();
    clear_reveal_timer();
    ws_ref.current.send(
      JSON.stringify({ type: "input_text.final", data: { text } })
    );
    on_user_transcript_ref.current(text);
    setStreamingText("");
    full_text_ref.current = "";
    audio_chunks_ref.current = [];
    setStatus("processing");
  }, []);

  // ── STT ────────────────────────────────────────────────────────────────────

  const { is_supported: is_stt_supported, is_listening, interim: interim_transcript, start: start_stt, stop: stop_stt } =
    use_speech_recognition({ on_final_transcript: send_transcript });

  // Keep STT refs in sync so callbacks always use the latest functions.
  useEffect(() => { start_stt_ref.current = start_stt; }, [start_stt]);
  useEffect(() => { stop_stt_ref.current = stop_stt; }, [stop_stt]);

  // ── WebSocket message handler ───────────────────────────────────────────────

  /**
   * Processes an incoming server event from the voice WebSocket.
   * Text deltas are buffered silently — only revealed during audio playback.
   */
  const handle_message = useCallback(
    (raw: string) => {
      let event: { type: string; data: Record<string, unknown> };
      try {
        event = JSON.parse(raw) as typeof event;
      } catch {
        console.error("[Voice] bad JSON from server");
        return;
      }
      console.log("[Voice WS] ←", event.type);

      switch (event.type) {
        case "session.ready":
          setStatus("listening");
          start_stt_ref.current();
          break;

        case "assistant.text.delta": {
          const chunk = (event.data.text as string) ?? "";
          full_text_ref.current += chunk;
          break;
        }

        case "assistant.text.done":
          setStatus("speaking");
          break;

        case "output_audio.chunk": {
          const b64 = (event.data.audio_b64 as string) ?? "";
          if (b64) audio_chunks_ref.current.push(b64);
          break;
        }

        case "output_audio.done":
          play_audio(full_text_ref.current);
          break;

        case "turn.done":
          on_assistant_message_ref.current(full_text_ref.current);
          break;

        case "error": {
          const code = String(event.data.code ?? "");
          const msg = String(event.data.message ?? "");
          console.warn("[Voice WS] backend error:", code, msg);
          if (code === "voice_stream_failed" && full_text_ref.current) {
            setStatus("speaking");
            const text = full_text_ref.current;
            const word_count = text.split(/\s+/).filter(Boolean).length;
            start_text_reveal(text, Math.max(word_count * 120, 500));
            speak_fallback(text, on_audio_ended);
          } else {
            const display = `[${code}] ${msg}`;
            on_error_ref.current?.(display);
            setStatus("error");
          }
          break;
        }

        case "pong":
          break;
      }
    },
    [play_audio, on_audio_ended]
  );

  // ── Connect / disconnect ────────────────────────────────────────────────────

  /**
   * Opens the voice WebSocket for the given conversation id and token.
   * On session.ready the mic starts automatically.
   */
  const connect = useCallback(
    async (conversation_id: string, token: string) => {
      if (ws_ref.current) return;

      setStatus("connecting");
      setStreamingText("");
      full_text_ref.current = "";
      audio_chunks_ref.current = [];
      is_busy_ref.current = false;
      clear_reveal_timer();

      const url = `${WS_BASE}/api/v1/voice/ws/${conversation_id}?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(url);
      ws_ref.current = ws;

      ws.onopen = () => console.log("[Voice WS] connected");
      ws.onmessage = (e: MessageEvent) => handle_message(e.data as string);
      ws.onerror = () => {
        console.error("[Voice WS] socket error");
        setStatus("error");
        on_error_ref.current?.("WebSocket error — is the backend running?");
      };
      ws.onclose = () => {
        console.log("[Voice WS] disconnected");
        ws_ref.current = null;
        is_busy_ref.current = false;
        setStatus("disconnected");
      };
    },
    [handle_message]
  );

  /**
   * Closes the WebSocket, stops the mic, cancels any ongoing audio/reveal.
   */
  const disconnect = useCallback(() => {
    window.speechSynthesis.cancel();
    clear_reveal_timer();
    stop_stt();
    ws_ref.current?.close();
    ws_ref.current = null;
    is_busy_ref.current = false;
    audio_chunks_ref.current = [];
    setStatus("disconnected");
    setStreamingText("");
  }, [stop_stt]);

  // Disconnect on unmount.
  useEffect(() => disconnect, [disconnect]);

  return {
    status,
    streaming_text,
    is_stt_supported,
    interim_transcript: is_listening ? interim_transcript : "",
    connect,
    disconnect,
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Speaks text via browser speechSynthesis as a TTS fallback.
 * Calls on_ended when the utterance finishes or errors.
 */
function speak_fallback(text: string, on_ended: () => void) {
  if (!text.trim()) { on_ended(); return; }
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 0.95;
  utter.lang = "en-US";
  utter.onend = on_ended;
  utter.onerror = () => on_ended();
  window.speechSynthesis.speak(utter);
}
