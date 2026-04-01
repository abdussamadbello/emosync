import { useState, useRef, useCallback, useEffect } from "react";

// ── Web Speech API type shim ──────────────────────────────────────────────────
interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}
interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string;
  readonly message: string;
}
interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}
declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
  }
}

interface UseSpeechRecognitionOptions {
  /** Called with the finalised transcript string on each complete utterance. */
  on_final_transcript: (text: string) => void;
  lang?: string;
}

interface UseSpeechRecognitionReturn {
  /** Whether the browser supports the Web Speech API. */
  is_supported: boolean;
  /** Whether recognition is currently active. */
  is_listening: boolean;
  /** In-progress (not yet finalised) words. */
  interim: string;
  /** Starts continuous recognition. No-ops if already listening. */
  start: () => void;
  /** Stops recognition. */
  stop: () => void;
}

/**
 * Thin wrapper around the browser Web Speech API (SpeechRecognition).
 * Runs in continuous + interim mode and fires on_final_transcript for
 * each finalised utterance. Supported in Chrome and Edge only.
 */
export function use_speech_recognition({
  on_final_transcript,
  lang = "en-US",
}: UseSpeechRecognitionOptions): UseSpeechRecognitionReturn {
  const [is_supported, setIsSupported] = useState(false);
  const [is_listening, setIsListening] = useState(false);
  const [interim, setInterim] = useState("");
  const recognition_ref = useRef<SpeechRecognitionInstance | null>(null);

  // Stable ref so callbacks set after mount always point to the latest handler.
  const on_final_ref = useRef(on_final_transcript);
  useEffect(() => { on_final_ref.current = on_final_transcript; }, [on_final_transcript]);

  useEffect(() => {
    setIsSupported(!!(window.SpeechRecognition ?? window.webkitSpeechRecognition));
  }, []);

  /**
   * Starts continuous speech recognition. Fires on_final_transcript for each
   * finalised result; interim text is exposed via the interim state value.
   */
  const start = useCallback(() => {
    const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Ctor || recognition_ref.current) return;

    const rec = new Ctor();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = lang;

    rec.onresult = (e: SpeechRecognitionEvent) => {
      let interim_text = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const text = e.results[i][0].transcript;
        if (e.results[i].isFinal) {
          const final = text.trim();
          if (final) {
            on_final_ref.current(final);
          }
          setInterim("");
        } else {
          interim_text += text;
        }
      }
      if (interim_text) setInterim(interim_text);
    };

    rec.onerror = (e: SpeechRecognitionErrorEvent) => {
      console.error("[STT] error:", e.error, e.message);
      setIsListening(false);
      setInterim("");
      recognition_ref.current = null;
    };

    rec.onend = () => {
      setIsListening(false);
      setInterim("");
      recognition_ref.current = null;
    };

    recognition_ref.current = rec;
    rec.start();
    setIsListening(true);
  }, [lang]);

  /**
   * Stops an active recognition session.
   */
  const stop = useCallback(() => {
    recognition_ref.current?.stop();
    recognition_ref.current = null;
    setIsListening(false);
    setInterim("");
  }, []);

  return { is_supported, is_listening, interim, start, stop };
}
