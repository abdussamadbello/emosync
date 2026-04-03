"use client";

import { useState, useRef, useCallback, useEffect } from "react";

const WS_BASE =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
    /^http/,
    "ws"
  );

/** Average byte-frequency amplitude (0–255) below which we consider silence. */
const SILENCE_THRESHOLD = 8;
/** Consecutive milliseconds of silence before committing the audio turn. */
const SILENCE_DURATION_MS = 1_400;
/** Minimum recording duration before silence detection can commit. */
const MIN_SPEECH_MS = 400;
/** MediaRecorder chunk interval in milliseconds. */
const CHUNK_INTERVAL_MS = 200;

export type VoiceChatStatus =
  | "disconnected"
  | "connecting"
  | "listening"
  | "processing"
  | "speaking"
  | "error";

interface UseVoiceChatOptions {
  /** Called when the backend confirms the user's transcribed utterance. */
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
  /** True when the browser supports getUserMedia (MediaRecorder-based, so universally true in modern browsers). */
  is_stt_supported: boolean;
  /** Always empty — server-side STT does not provide interim transcripts. */
  interim_transcript: string;
  /**
   * Opens the voice WebSocket for the given conversation and starts the mic.
   * Audio is streamed to the backend for ElevenLabs STT.
   */
  connect: (conversation_id: string, token: string) => Promise<void>;
  /** Closes the WebSocket, stops the mic, and cancels any ongoing audio. */
  disconnect: () => void;
}

/**
 * Manages the full voice-to-voice loop using server-side ElevenLabs STT:
 *   MediaRecorder mic → input_audio.append chunks → backend STT → agent → ElevenLabs TTS
 *
 * Silence detection (via AnalyserNode) auto-commits the audio turn after
 * SILENCE_DURATION_MS of quiet following at least MIN_SPEECH_MS of speech.
 * The backend sends back a user.transcript event so the transcript appears
 * in the chat, followed by the streamed assistant response + audio.
 */
export function use_voice_chat({
  on_user_transcript,
  on_assistant_message,
  on_assistant_delta,
  on_error,
}: UseVoiceChatOptions): UseVoiceChatReturn {
  const [status, setStatus] = useState<VoiceChatStatus>("disconnected");
  const [streaming_text, setStreamingText] = useState("");
  const [is_stt_supported, setIsSttSupported] = useState(false);

  // WebSocket
  const ws_ref = useRef<WebSocket | null>(null);

  // TTS playback buffers
  const audio_chunks_ref = useRef<string[]>([]);
  const full_text_ref = useRef("");
  const reveal_timer_ref = useRef<number | null>(null);

  // Mic / recording refs
  const media_recorder_ref = useRef<MediaRecorder | null>(null);
  const stream_ref = useRef<MediaStream | null>(null);
  const audio_ctx_ref = useRef<AudioContext | null>(null);
  const analyser_ref = useRef<AnalyserNode | null>(null);
  const silence_check_ref = useRef<number | null>(null);
  const silence_start_ref = useRef<number | null>(null);
  const recording_start_ref = useRef<number>(0);
  const mime_type_ref = useRef<string>("audio/webm");

  // Pending async chunk encodes — used to drain before sending commit.
  const pending_sends_ref = useRef(0);
  const commit_pending_ref = useRef(false);

  // Busy guard: true while backend is processing or speaking
  const is_busy_ref = useRef(false);

  // Stable callback refs so WS handlers always call the latest versions.
  const on_user_transcript_ref = useRef(on_user_transcript);
  const on_assistant_message_ref = useRef(on_assistant_message);
  const on_assistant_delta_ref = useRef(on_assistant_delta);
  const on_error_ref = useRef(on_error);
  useEffect(() => { on_user_transcript_ref.current = on_user_transcript; }, [on_user_transcript]);
  useEffect(() => { on_assistant_message_ref.current = on_assistant_message; }, [on_assistant_message]);
  useEffect(() => { on_assistant_delta_ref.current = on_assistant_delta; }, [on_assistant_delta]);
  useEffect(() => { on_error_ref.current = on_error; }, [on_error]);

  // Stable refs for start/stop mic (called from WS callbacks without re-renders).
  const start_mic_ref = useRef<() => Promise<void>>(async () => {});
  const stop_mic_ref = useRef<() => void>(() => {});

  useEffect(() => {
    setIsSttSupported(!!navigator.mediaDevices?.getUserMedia);
  }, []);

  // ── Text reveal ─────────────────────────────────────────────────────────────

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
   * spaced evenly over duration_ms so text appears in sync with audio playback.
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
   * Called when audio playback finishes (ElevenLabs or browser fallback).
   * Resets busy state and restarts the mic for the next user turn.
   */
  const on_audio_ended = useCallback(() => {
    clear_reveal_timer();
    is_busy_ref.current = false;
    setStatus("listening");
    void start_mic_ref.current();
  }, []);

  /**
   * Decodes buffered base64 TTS audio chunks, plays them via AudioContext,
   * and synchronises the word-by-word text reveal to audio duration.
   * Falls back to browser speechSynthesis if AudioContext decode fails.
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

  // ── Mic control ─────────────────────────────────────────────────────────────

  /**
   * Stops recording, silence detection, and releases all mic/audio resources.
   */
  const stop_mic = useCallback(() => {
    if (silence_check_ref.current !== null) {
      window.clearInterval(silence_check_ref.current);
      silence_check_ref.current = null;
    }
    silence_start_ref.current = null;
    analyser_ref.current = null;

    if (media_recorder_ref.current?.state !== "inactive") {
      media_recorder_ref.current?.stop();
    }
    media_recorder_ref.current = null;

    stream_ref.current?.getTracks().forEach((t) => t.stop());
    stream_ref.current = null;
    audio_ctx_ref.current?.close();
    audio_ctx_ref.current = null;
  }, []);

  /**
   * Sends the commit event to the backend after all pending audio chunks
   * have been encoded and sent.  Called either immediately (no pending chunks)
   * or deferred until the last arrayBuffer() resolves.
   */
  const do_commit = useCallback(() => {
    const mime = mime_type_ref.current;
    if (ws_ref.current?.readyState === WebSocket.OPEN) {
      ws_ref.current.send(
        JSON.stringify({ type: "input_audio.commit", data: { mime_type: mime } })
      );
    }
    setStatus("processing");
    // Release mic resources after commit (recorder was already stopped).
    stream_ref.current?.getTracks().forEach((t) => t.stop());
    stream_ref.current = null;
    audio_ctx_ref.current?.close();
    audio_ctx_ref.current = null;
    media_recorder_ref.current = null;
  }, []);

  /**
   * Stops the MediaRecorder (flushing the last chunk) then sends
   * input_audio.commit once all buffered chunks have been transmitted.
   */
  const commit_audio = useCallback(() => {
    if (ws_ref.current?.readyState !== WebSocket.OPEN) return;
    if (is_busy_ref.current) return;
    is_busy_ref.current = true;

    if (silence_check_ref.current !== null) {
      window.clearInterval(silence_check_ref.current);
      silence_check_ref.current = null;
    }
    silence_start_ref.current = null;
    analyser_ref.current = null;

    const recorder = media_recorder_ref.current;
    if (recorder && recorder.state !== "inactive") {
      // Mark that commit should fire once all pending sends drain.
      commit_pending_ref.current = true;
      recorder.stop();
    } else {
      // No active recorder — commit immediately if nothing is in flight.
      if (pending_sends_ref.current === 0) {
        do_commit();
      } else {
        commit_pending_ref.current = true;
      }
    }
  }, [do_commit]);

  /**
   * Requests mic access, creates an AudioContext + AnalyserNode for silence
   * detection, and starts a MediaRecorder that streams base64 audio chunks
   * to the backend every CHUNK_INTERVAL_MS milliseconds.
   */
  const start_mic = useCallback(async () => {
    if (is_busy_ref.current || media_recorder_ref.current) return;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      console.error("[Voice] mic access denied:", err);
      on_error_ref.current?.("Microphone access denied.");
      setStatus("error");
      return;
    }

    stream_ref.current = stream;
    const audio_ctx = new AudioContext();
    audio_ctx_ref.current = audio_ctx;
    const source = audio_ctx.createMediaStreamSource(stream);
    const analyser = audio_ctx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    analyser_ref.current = analyser;

    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : "audio/mp4";
    mime_type_ref.current = mime;

    const recorder = new MediaRecorder(stream, { mimeType: mime });
    media_recorder_ref.current = recorder;
    recording_start_ref.current = Date.now();
    silence_start_ref.current = null;
    pending_sends_ref.current = 0;
    commit_pending_ref.current = false;

    recorder.ondataavailable = (e) => {
      if (e.data.size === 0) return;
      pending_sends_ref.current++;
      void e.data.arrayBuffer().then((buf) => {
        const bytes = new Uint8Array(buf);
        // Build base64 in chunks to avoid call-stack limits on large buffers.
        const CHUNK = 8_192;
        let binary = "";
        for (let i = 0; i < bytes.length; i += CHUNK) {
          binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
        }
        const b64 = btoa(binary);
        pending_sends_ref.current--;

        if (ws_ref.current?.readyState === WebSocket.OPEN) {
          ws_ref.current.send(
            JSON.stringify({ type: "input_audio.append", data: { audio: b64 } })
          );
        }

        // If commit_audio was called while this chunk was in flight, send now.
        if (pending_sends_ref.current === 0 && commit_pending_ref.current) {
          commit_pending_ref.current = false;
          do_commit();
        }
      });
    };

    recorder.start(CHUNK_INTERVAL_MS);

    // Silence detection: poll analyser every 100ms.
    const freq_data = new Uint8Array(analyser.frequencyBinCount);
    silence_check_ref.current = window.setInterval(() => {
      const an = analyser_ref.current;
      if (!an) return;
      an.getByteFrequencyData(freq_data);
      const avg = freq_data.reduce((s, v) => s + v, 0) / freq_data.length;
      const elapsed = Date.now() - recording_start_ref.current;

      if (avg < SILENCE_THRESHOLD && elapsed > MIN_SPEECH_MS) {
        if (silence_start_ref.current === null) {
          silence_start_ref.current = Date.now();
        } else if (Date.now() - silence_start_ref.current >= SILENCE_DURATION_MS) {
          console.log("[Voice] silence detected — committing audio");
          commit_audio();
        }
      } else {
        silence_start_ref.current = null;
      }
    }, 100);

    setStatus("listening");
    console.log("[Voice] mic started, mime:", mime);
  }, [commit_audio, do_commit]);

  useEffect(() => { start_mic_ref.current = start_mic; }, [start_mic]);
  useEffect(() => { stop_mic_ref.current = stop_mic; }, [stop_mic]);

  // ── WebSocket message handler ───────────────────────────────────────────────

  /**
   * Dispatches incoming server events from the voice WebSocket.
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
          void start_mic_ref.current();
          break;

        case "user.transcript": {
          const text = (event.data.text as string) ?? "";
          if (text) {
            on_user_transcript_ref.current(text);
            setStreamingText("");
            full_text_ref.current = "";
            audio_chunks_ref.current = [];
          }
          break;
        }

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
          void play_audio(full_text_ref.current);
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
            on_error_ref.current?.(`[${code}] ${msg}`);
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
   * Opens the voice WebSocket for the given conversation id.
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
   * Closes the WebSocket, stops the mic, cancels audio playback and text reveal.
   */
  const disconnect = useCallback(() => {
    window.speechSynthesis.cancel();
    clear_reveal_timer();
    stop_mic();
    ws_ref.current?.close();
    ws_ref.current = null;
    is_busy_ref.current = false;
    audio_chunks_ref.current = [];
    setStatus("disconnected");
    setStreamingText("");
  }, [stop_mic]);

  useEffect(() => disconnect, [disconnect]);

  return {
    status,
    streaming_text,
    is_stt_supported,
    interim_transcript: "",
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
