"use client";

import { useState, useRef, useCallback, useEffect } from "react";

const WS_BASE =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
    /^http/,
    "ws"
  );

const SILENCE_THRESHOLD = 8;
const SILENCE_DURATION_MS = 1_400;
const MIN_SPEECH_MS = 400;
const LEGACY_CHUNK_INTERVAL_MS = 200;
const LIVE_PROCESSOR_BUFFER_SIZE = 4_096;
const LIVE_PLAYBACK_LEAD_SECONDS = 0.05;
const TURN_INACTIVITY_TIMEOUT_MS = 15_000;

type VoiceProvider = "unknown" | "gemini_live" | "legacy";

export type VoiceChatStatus =
  | "disconnected"
  | "connecting"
  | "listening"
  | "processing"
  | "speaking"
  | "error";

interface UseVoiceChatOptions {
  on_user_transcript: (text: string) => void;
  on_assistant_message: (text: string) => void;
  on_assistant_delta: (delta: string) => void;
  on_error?: (msg: string) => void;
}

interface UseVoiceChatReturn {
  status: VoiceChatStatus;
  streaming_text: string;
  is_stt_supported: boolean;
  interim_transcript: string;
  connect: (conversation_id: string, token: string) => Promise<void>;
  disconnect: () => void;
}

function useVoiceChat({
  on_user_transcript,
  on_assistant_message,
  on_assistant_delta,
  on_error,
}: UseVoiceChatOptions): UseVoiceChatReturn {
  const [status, setStatus] = useState<VoiceChatStatus>("disconnected");
  const [streaming_text, setStreamingText] = useState("");
  const [interim_transcript, setInterimTranscript] = useState("");
  const [is_stt_supported, setIsSttSupported] = useState(false);

  const ws_ref = useRef<WebSocket | null>(null);
  const provider_ref = useRef<VoiceProvider>("unknown");

  const full_text_ref = useRef("");
  const legacy_audio_chunks_ref = useRef<string[]>([]);
  const reveal_timer_ref = useRef<number | null>(null);
  const turn_timeout_ref = useRef<number | null>(null);
  const waiting_for_response_ref = useRef(false);
  const has_started_response_ref = useRef(false);

  const capture_stream_ref = useRef<MediaStream | null>(null);
  const capture_ctx_ref = useRef<AudioContext | null>(null);
  const analyser_ref = useRef<AnalyserNode | null>(null);
  const source_ref = useRef<MediaStreamAudioSourceNode | null>(null);
  const mute_gain_ref = useRef<GainNode | null>(null);
  const live_processor_ref = useRef<ScriptProcessorNode | null>(null);
  const legacy_recorder_ref = useRef<MediaRecorder | null>(null);
  const silence_check_ref = useRef<number | null>(null);
  const silence_start_ref = useRef<number | null>(null);
  const recording_start_ref = useRef<number>(0);
  const legacy_mime_type_ref = useRef<string>("audio/webm");
  const live_input_sample_rate_ref = useRef<number>(16_000);

  const pending_sends_ref = useRef(0);
  const commit_pending_ref = useRef(false);

  const playback_ctx_ref = useRef<AudioContext | null>(null);
  const playback_next_time_ref = useRef(0);
  const playback_end_timer_ref = useRef<number | null>(null);
  const playback_done_ref = useRef(false);
  const playback_has_audio_ref = useRef(false);

  const is_busy_ref = useRef(false);
  const is_mounted_ref = useRef(true);

  const on_user_transcript_ref = useRef(on_user_transcript);
  const on_assistant_message_ref = useRef(on_assistant_message);
  const on_assistant_delta_ref = useRef(on_assistant_delta);
  const on_error_ref = useRef(on_error);
  useEffect(() => { on_user_transcript_ref.current = on_user_transcript; }, [on_user_transcript]);
  useEffect(() => { on_assistant_message_ref.current = on_assistant_message; }, [on_assistant_message]);
  useEffect(() => { on_assistant_delta_ref.current = on_assistant_delta; }, [on_assistant_delta]);
  useEffect(() => { on_error_ref.current = on_error; }, [on_error]);

  const start_mic_ref = useRef<() => Promise<void>>(async () => {});
  const stop_mic_ref = useRef<() => void>(() => {});

  useEffect(() => {
    setIsSttSupported(!!navigator.mediaDevices?.getUserMedia);
  }, []);

  function clear_reveal_timer() {
    if (reveal_timer_ref.current !== null) {
      window.clearInterval(reveal_timer_ref.current);
      reveal_timer_ref.current = null;
    }
  }

  function clear_playback_end_timer() {
    if (playback_end_timer_ref.current !== null) {
      window.clearTimeout(playback_end_timer_ref.current);
      playback_end_timer_ref.current = null;
    }
  }

  function clear_turn_timeout() {
    if (turn_timeout_ref.current !== null) {
      window.clearTimeout(turn_timeout_ref.current);
      turn_timeout_ref.current = null;
    }
  }

  function clear_silence_timer() {
    if (silence_check_ref.current !== null) {
      window.clearInterval(silence_check_ref.current);
      silence_check_ref.current = null;
    }
    silence_start_ref.current = null;
  }

  const reset_response_buffers = useCallback(() => {
    full_text_ref.current = "";
    legacy_audio_chunks_ref.current = [];
    setStreamingText("");
  }, []);

  const reset_turn_buffers = useCallback(() => {
    reset_response_buffers();
    waiting_for_response_ref.current = true;
    has_started_response_ref.current = false;
    playback_done_ref.current = false;
    playback_has_audio_ref.current = false;
    playback_next_time_ref.current = 0;
  }, [reset_response_buffers]);

  const start_text_reveal = useCallback((text: string, duration_ms: number) => {
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
  }, []);

  const stop_live_playback = useCallback(() => {
    clear_playback_end_timer();
    playback_next_time_ref.current = 0;
    playback_done_ref.current = false;
    playback_has_audio_ref.current = false;
    void playback_ctx_ref.current?.close();
    playback_ctx_ref.current = null;
  }, []);

  const on_audio_ended = useCallback(() => {
    clear_reveal_timer();
    clear_playback_end_timer();
    stop_live_playback();
    is_busy_ref.current = false;
    setInterimTranscript("");
    // Reset text buffers so subsequent turns don't accumulate old text
    full_text_ref.current = "";
    setStreamingText("");
    setStatus("listening");
    void start_mic_ref.current();
  }, [stop_live_playback]);

  const recover_from_stalled_turn = useCallback((message: string) => {
    clear_turn_timeout();
    clear_reveal_timer();
    stop_live_playback();
    stop_mic_ref.current();
    reset_turn_buffers();
    waiting_for_response_ref.current = false;
    has_started_response_ref.current = false;
    is_busy_ref.current = false;
    setInterimTranscript("");
    on_user_transcript_ref.current("");
    setStatus("listening");
    on_error_ref.current?.(message);

    if (ws_ref.current?.readyState === WebSocket.OPEN) {
      ws_ref.current.send(JSON.stringify({ type: "turn.cancel", data: {} }));
    }

    void start_mic_ref.current();
  }, [reset_turn_buffers, stop_live_playback]);

  const arm_turn_timeout = useCallback(() => {
    if (!waiting_for_response_ref.current || has_started_response_ref.current) return;
    clear_turn_timeout();
    turn_timeout_ref.current = window.setTimeout(() => {
      recover_from_stalled_turn("Voice turn timed out. Please try again.");
    }, TURN_INACTIVITY_TIMEOUT_MS);
  }, [recover_from_stalled_turn]);

  const schedule_live_playback_end = useCallback(() => {
    if (!playback_done_ref.current) return;
    const ctx = playback_ctx_ref.current;
    if (!ctx) {
      on_audio_ended();
      return;
    }
    const remaining_ms = Math.max(
      (playback_next_time_ref.current - ctx.currentTime) * 1000 + 40,
      0
    );
    clear_playback_end_timer();
    playback_end_timer_ref.current = window.setTimeout(() => {
      on_audio_ended();
    }, remaining_ms);
  }, [on_audio_ended]);

  const play_legacy_audio = useCallback(
    async () => {
      const chunks = legacy_audio_chunks_ref.current;
      const text = full_text_ref.current;

      if (chunks.length === 0) {
        const word_count = text.split(/\s+/).filter(Boolean).length;
        start_text_reveal(text, Math.max(word_count * 120, 500));
        window.setTimeout(on_audio_ended, Math.max(word_count * 120, 500) + 500);
        return;
      }

      const byte_arrays = chunks.map((b64) => base64ToUint8Array(b64));
      const total = byte_arrays.reduce((sum, item) => sum + item.length, 0);
      const bytes = new Uint8Array(total);
      let offset = 0;
      for (const chunk of byte_arrays) {
        bytes.set(chunk, offset);
        offset += chunk.length;
      }

      try {
        const ctx = new AudioContext();
        const buf = await ctx.decodeAudioData(bytes.buffer.slice(0));
        const src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(ctx.destination);
        src.onended = on_audio_ended;
        src.start(0);
        start_text_reveal(text, buf.duration * 1000);
      } catch {
        const word_count = text.split(/\s+/).filter(Boolean).length;
        start_text_reveal(text, Math.max(word_count * 120, 500));
        window.setTimeout(on_audio_ended, Math.max(word_count * 120, 500) + 500);
      }
    },
    [on_audio_ended, start_text_reveal]
  );

  const enqueue_live_audio_chunk = useCallback(
    async (audio_b64: string, sample_rate_hz: number) => {
      if (!audio_b64) return;

      let ctx = playback_ctx_ref.current;
      if (!ctx) {
        ctx = new AudioContext();
        playback_ctx_ref.current = ctx;
        playback_next_time_ref.current = ctx.currentTime + LIVE_PLAYBACK_LEAD_SECONDS;
      }
      if (ctx.state === "suspended") {
        await ctx.resume();
      }

      const bytes = base64ToUint8Array(audio_b64);
      const samples = pcm16leToFloat32(bytes);
      if (samples.length === 0) return;

      const buffer = ctx.createBuffer(1, samples.length, sample_rate_hz);
      buffer.copyToChannel(new Float32Array(samples), 0);

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);

      const start_at = Math.max(
        ctx.currentTime + LIVE_PLAYBACK_LEAD_SECONDS,
        playback_next_time_ref.current
      );
      source.start(start_at);

      playback_has_audio_ref.current = true;
      playback_next_time_ref.current = start_at + buffer.duration;
      setStatus("speaking");

      if (playback_done_ref.current) {
        schedule_live_playback_end();
      }
    },
    [schedule_live_playback_end]
  );

  const stop_capture_resources = useCallback(() => {
    clear_silence_timer();

    const recorder = legacy_recorder_ref.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
    legacy_recorder_ref.current = null;

    if (live_processor_ref.current) {
      live_processor_ref.current.disconnect();
      live_processor_ref.current.onaudioprocess = null;
    }
    live_processor_ref.current = null;
    source_ref.current?.disconnect();
    source_ref.current = null;
    analyser_ref.current?.disconnect();
    analyser_ref.current = null;
    mute_gain_ref.current?.disconnect();
    mute_gain_ref.current = null;

    capture_stream_ref.current?.getTracks().forEach((track) => track.stop());
    capture_stream_ref.current = null;
    void capture_ctx_ref.current?.close();
    capture_ctx_ref.current = null;
    setInterimTranscript("");
  }, []);

  const do_commit = useCallback(() => {
    if (ws_ref.current?.readyState !== WebSocket.OPEN) return;

    reset_response_buffers();
    waiting_for_response_ref.current = true;
    has_started_response_ref.current = false;
    on_user_transcript_ref.current("…");
    arm_turn_timeout();

    if (provider_ref.current === "gemini_live") {
      ws_ref.current.send(
        JSON.stringify({
          type: "input_audio.commit",
          data: {
            mime_type: `audio/pcm;rate=${live_input_sample_rate_ref.current}`,
          },
        })
      );
      setStatus("processing");
      stop_capture_resources();
      return;
    }

    ws_ref.current.send(
      JSON.stringify({
        type: "input_audio.commit",
        data: { mime_type: legacy_mime_type_ref.current },
      })
    );
    setStatus("processing");
    stop_capture_resources();
  }, [arm_turn_timeout, reset_response_buffers, stop_capture_resources]);

  const commit_audio = useCallback(() => {
    if (ws_ref.current?.readyState !== WebSocket.OPEN) return;
    if (is_busy_ref.current) return;
    is_busy_ref.current = true;
    clear_silence_timer();

    if (provider_ref.current === "gemini_live") {
      do_commit();
      return;
    }

    const recorder = legacy_recorder_ref.current;
    if (recorder && recorder.state !== "inactive") {
      commit_pending_ref.current = true;
      recorder.stop();
    } else if (pending_sends_ref.current === 0) {
      do_commit();
    } else {
      commit_pending_ref.current = true;
    }
  }, [do_commit]);

  const start_silence_detection = useCallback(() => {
    const analyser = analyser_ref.current;
    if (!analyser) return;

    const freq_data = new Uint8Array(analyser.frequencyBinCount);
    silence_check_ref.current = window.setInterval(() => {
      const active_analyser = analyser_ref.current;
      if (!active_analyser) return;

      active_analyser.getByteFrequencyData(freq_data);
      const avg = freq_data.reduce((sum, value) => sum + value, 0) / freq_data.length;
      const elapsed = Date.now() - recording_start_ref.current;

      if (avg < SILENCE_THRESHOLD && elapsed > MIN_SPEECH_MS) {
        if (silence_start_ref.current === null) {
          silence_start_ref.current = Date.now();
        } else if (Date.now() - silence_start_ref.current >= SILENCE_DURATION_MS) {
          commit_audio();
        }
      } else {
        silence_start_ref.current = null;
      }
    }, 100);
  }, [commit_audio]);

  const start_live_mic = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    capture_stream_ref.current = stream;
    const ctx = new AudioContext();
    capture_ctx_ref.current = ctx;

    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    const processor = ctx.createScriptProcessor(LIVE_PROCESSOR_BUFFER_SIZE, 1, 1);
    const mute_gain = ctx.createGain();
    mute_gain.gain.value = 0;

    source.connect(analyser);
    source.connect(processor);
    processor.connect(mute_gain);
    mute_gain.connect(ctx.destination);

    processor.onaudioprocess = (event: AudioProcessingEvent) => {
      if (is_busy_ref.current) return;
      if (ws_ref.current?.readyState !== WebSocket.OPEN) return;

      const input = event.inputBuffer.getChannelData(0);
      const pcm_bytes = float32ToPcm16Bytes(
        downsampleFloat32(input, ctx.sampleRate, live_input_sample_rate_ref.current)
      );
      if (pcm_bytes.length === 0) return;

      ws_ref.current.send(
        JSON.stringify({
          type: "input_audio.append",
          data: {
            audio: uint8ArrayToBase64(pcm_bytes),
            mime_type: `audio/pcm;rate=${live_input_sample_rate_ref.current}`,
          },
        })
      );
    };

    source_ref.current = source;
    analyser_ref.current = analyser;
    live_processor_ref.current = processor;
    mute_gain_ref.current = mute_gain;
    recording_start_ref.current = Date.now();
    silence_start_ref.current = null;
    start_silence_detection();
    setStatus("listening");
  }, [start_silence_detection]);

  const start_legacy_mic = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    capture_stream_ref.current = stream;
    const ctx = new AudioContext();
    capture_ctx_ref.current = ctx;

    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    source_ref.current = source;
    analyser_ref.current = analyser;

    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : "audio/mp4";

    legacy_mime_type_ref.current = mime;
    pending_sends_ref.current = 0;
    commit_pending_ref.current = false;
    recording_start_ref.current = Date.now();
    silence_start_ref.current = null;

    const recorder = new MediaRecorder(stream, { mimeType: mime });
    legacy_recorder_ref.current = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size === 0) return;
      pending_sends_ref.current++;
      void event.data.arrayBuffer().then((buf) => {
        pending_sends_ref.current--;
        if (ws_ref.current?.readyState === WebSocket.OPEN) {
          ws_ref.current.send(
            JSON.stringify({
              type: "input_audio.append",
              data: {
                audio: uint8ArrayToBase64(new Uint8Array(buf)),
              },
            })
          );
        }

        if (pending_sends_ref.current === 0 && commit_pending_ref.current) {
          commit_pending_ref.current = false;
          do_commit();
        }
      });
    };

    recorder.start(LEGACY_CHUNK_INTERVAL_MS);
    start_silence_detection();
    setStatus("listening");
  }, [do_commit, start_silence_detection]);

  const start_mic = useCallback(async () => {
    if (is_busy_ref.current) return;
    if (capture_stream_ref.current || legacy_recorder_ref.current || live_processor_ref.current) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      on_error_ref.current?.("Microphone access is not available in this browser.");
      setStatus("error");
      return;
    }

    try {
      if (provider_ref.current === "gemini_live") {
        await start_live_mic();
      } else {
        await start_legacy_mic();
      }
    } catch {
      on_error_ref.current?.("Microphone access denied.");
      setStatus("error");
    }
  }, [start_legacy_mic, start_live_mic]);

  const stop_mic = useCallback(() => {
    stop_capture_resources();
  }, [stop_capture_resources]);

  useEffect(() => { start_mic_ref.current = start_mic; }, [start_mic]);
  useEffect(() => { stop_mic_ref.current = stop_mic; }, [stop_mic]);

  const handle_message = useCallback(
    (raw: string) => {
      let event: { type: string; data: Record<string, unknown> };
      try {
        event = JSON.parse(raw) as typeof event;
      } catch {
        return;
      }

      switch (event.type) {
        case "session.ready": {
          clear_turn_timeout();
          provider_ref.current =
            event.data.provider === "legacy" ? "legacy" : "gemini_live";
          live_input_sample_rate_ref.current = Number(
            event.data.input_sample_rate_hz ?? 16_000
          );
          reset_turn_buffers();
    waiting_for_response_ref.current = false;
    has_started_response_ref.current = false;
          setInterimTranscript("");
          setStreamingText("");
          setStatus("listening");
          void start_mic_ref.current();
          break;
        }

        case "user.transcript": {
          arm_turn_timeout();
          const text = String(event.data.text ?? "");
          if (text) {
            on_user_transcript_ref.current(text);
            setInterimTranscript(text);
          }
          break;
        }

        case "assistant.text.delta": {
          has_started_response_ref.current = true;
          clear_turn_timeout();
          const chunk = String(event.data.text ?? "");
          if (!chunk) break;
          if (provider_ref.current === "gemini_live") {
            full_text_ref.current += chunk;
            setStreamingText((prev) => prev + chunk);
            on_assistant_delta_ref.current(chunk);
            setStatus("speaking");
            stop_mic_ref.current();
          } else {
            full_text_ref.current += chunk;
          }
          break;
        }

        case "assistant.text.done":
          arm_turn_timeout();
          setStatus("speaking");
          break;

        case "output_audio.chunk": {
          has_started_response_ref.current = true;
          clear_turn_timeout();
          const audio_b64 = String(event.data.audio_b64 ?? "");
          const mime_type = String(event.data.mime_type ?? "");
          const sample_rate_hz = Number(event.data.sample_rate_hz ?? 24_000);

          if (provider_ref.current === "gemini_live" || mime_type.startsWith("audio/pcm")) {
            stop_mic_ref.current();
            void enqueue_live_audio_chunk(audio_b64, sample_rate_hz);
          } else if (audio_b64) {
            const current_size = legacy_audio_chunks_ref.current.reduce(
              (sum, item) => sum + item.length,
              0
            );
            if (current_size + audio_b64.length < 50_000_000) {
              legacy_audio_chunks_ref.current.push(audio_b64);
            }
          }
          break;
        }

        case "output_audio.done":
          waiting_for_response_ref.current = false;
          has_started_response_ref.current = false;
          clear_turn_timeout();
          if (provider_ref.current === "gemini_live") {
            playback_done_ref.current = true;
            if (!playback_has_audio_ref.current) {
              const text = full_text_ref.current;
              if (text.trim()) {
                const word_count = text.split(/\s+/).filter(Boolean).length;
                start_text_reveal(text, Math.max(word_count * 120, 500));
                window.setTimeout(on_audio_ended, Math.max(word_count * 120, 500) + 500);
              } else {
                on_audio_ended();
              }
            } else {
              schedule_live_playback_end();
            }
          } else {
            void play_legacy_audio();
          }
          break;

        case "turn.interrupted":
          clear_turn_timeout();
          clear_reveal_timer();
          stop_live_playback();
          is_busy_ref.current = false;
          setInterimTranscript("");
          setStatus("listening");
          void start_mic_ref.current();
          break;

        case "turn.done":
          waiting_for_response_ref.current = false;
          has_started_response_ref.current = false;
          clear_turn_timeout();
          setInterimTranscript("");
          if (!event.data.cancelled) {
            on_assistant_message_ref.current(full_text_ref.current);
          } else {
            on_user_transcript_ref.current("");
          }
          // Reset text buffers so the next turn starts fresh
          full_text_ref.current = "";
          setStreamingText("");
          break;

        case "error": {
          clear_turn_timeout();
          const code = String(event.data.code ?? "");
          const msg = String(event.data.message ?? "");

          if (provider_ref.current === "legacy" && code === "voice_stream_failed" && full_text_ref.current) {
            setStatus("speaking");
            const text = full_text_ref.current;
            const word_count = text.split(/\s+/).filter(Boolean).length;
            start_text_reveal(text, Math.max(word_count * 120, 500));
            window.setTimeout(on_audio_ended, Math.max(word_count * 120, 500) + 500);
          } else {
            setInterimTranscript("");
            on_error_ref.current?.(`[${code}] ${msg}`);
            setStatus("error");
          }
          break;
        }

        case "pong":
          break;
      }
    },
    [
      arm_turn_timeout,
      enqueue_live_audio_chunk,
      on_audio_ended,
      play_legacy_audio,
      reset_turn_buffers,
      schedule_live_playback_end,
      start_text_reveal,
      stop_live_playback,
    ]
  );

  const connect = useCallback(
    async (conversation_id: string, token: string) => {
      if (ws_ref.current) return;

      provider_ref.current = "unknown";
      setStatus("connecting");
      setInterimTranscript("");
      setStreamingText("");
      reset_turn_buffers();
    waiting_for_response_ref.current = false;
    has_started_response_ref.current = false;
      is_busy_ref.current = false;
      clear_reveal_timer();
      clear_turn_timeout();
      stop_live_playback();

      const url = `${WS_BASE}/api/v1/voice/ws/${conversation_id}`;
      const ws = new WebSocket(url);
      ws_ref.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: "auth", data: { token } }));
      };
      ws.onmessage = (event: MessageEvent) => handle_message(event.data as string);
      ws.onerror = () => {
        if (!is_mounted_ref.current) return;
        clear_turn_timeout();
        setStatus("error");
        on_error_ref.current?.("WebSocket error — is the backend running?");
      };
      ws.onclose = () => {
        ws_ref.current = null;
        is_busy_ref.current = false;
        clear_turn_timeout();
        if (is_mounted_ref.current) setStatus("disconnected");
      };
    },
    [handle_message, reset_turn_buffers, stop_live_playback]
  );

  const disconnect = useCallback(() => {
        clear_reveal_timer();
    clear_playback_end_timer();
    clear_turn_timeout();
    waiting_for_response_ref.current = false;
    has_started_response_ref.current = false;
    stop_live_playback();
    stop_mic_ref.current();
    ws_ref.current?.close();
    ws_ref.current = null;
    is_busy_ref.current = false;
    reset_turn_buffers();
    waiting_for_response_ref.current = false;
    has_started_response_ref.current = false;
    setStatus("disconnected");
    setInterimTranscript("");
    setStreamingText("");
  }, [reset_turn_buffers, stop_live_playback]);

  useEffect(() => {
    is_mounted_ref.current = true;
    return () => {
      is_mounted_ref.current = false;
      disconnect();
    };
  }, [disconnect]);

  return {
    status,
    streaming_text,
    is_stt_supported,
    interim_transcript,
    connect,
    disconnect,
  };
}

export const use_voice_chat = useVoiceChat;

function base64ToUint8Array(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function uint8ArrayToBase64(bytes: Uint8Array): string {
  const chunk_size = 8_192;
  let binary = "";
  for (let i = 0; i < bytes.length; i += chunk_size) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk_size));
  }
  return btoa(binary);
}

function downsampleFloat32(
  input: Float32Array,
  source_rate: number,
  target_rate: number
): Float32Array {
  if (target_rate >= source_rate) return input;
  const ratio = source_rate / target_rate;
  const output_length = Math.round(input.length / ratio);
  const output = new Float32Array(output_length);
  let output_index = 0;
  let input_index = 0;

  while (output_index < output_length) {
    const next_index = Math.round((output_index + 1) * ratio);
    let sum = 0;
    let count = 0;
    for (let i = input_index; i < next_index && i < input.length; i++) {
      sum += input[i];
      count++;
    }
    output[output_index] = count > 0 ? sum / count : 0;
    output_index++;
    input_index = next_index;
  }

  return output;
}

function float32ToPcm16Bytes(input: Float32Array): Uint8Array {
  const output = new Uint8Array(input.length * 2);
  const view = new DataView(output.buffer);
  for (let i = 0; i < input.length; i++) {
    const sample = Math.max(-1, Math.min(1, input[i]));
    view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return output;
}

function pcm16leToFloat32(bytes: Uint8Array): Float32Array {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const sample_count = Math.floor(bytes.byteLength / 2);
  const output = new Float32Array(sample_count);
  for (let i = 0; i < sample_count; i++) {
    output[i] = view.getInt16(i * 2, true) / 0x8000;
  }
  return output;
}

