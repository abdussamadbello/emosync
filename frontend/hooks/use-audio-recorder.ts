import { useState, useRef, useCallback } from "react";

interface UseAudioRecorderReturn {
  is_recording: boolean;
  audio_blob: Blob | null;
  start_recording: () => Promise<void>;
  stop_recording: () => void;
  analyser_node: AnalyserNode | null;
}

export function use_audio_recorder(): UseAudioRecorderReturn {
  const [is_recording, setIsRecording] = useState(false);
  const [audio_blob, setAudioBlob] = useState<Blob | null>(null);
  const [analyser_node, setAnalyserNode] = useState<AnalyserNode | null>(null);
  const media_recorder_ref = useRef<MediaRecorder | null>(null);
  const chunks_ref = useRef<Blob[]>([]);

  const start_recording = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audio_context = new AudioContext();
    const source = audio_context.createMediaStreamSource(stream);
    const analyser = audio_context.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    setAnalyserNode(analyser);

    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    chunks_ref.current = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks_ref.current.push(e.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunks_ref.current, { type: "audio/webm" });
      setAudioBlob(blob);
      stream.getTracks().forEach((t) => t.stop());
      audio_context.close();
      setAnalyserNode(null);
    };

    media_recorder_ref.current = recorder;
    recorder.start();
    setIsRecording(true);
  }, []);

  const stop_recording = useCallback(() => {
    media_recorder_ref.current?.stop();
    setIsRecording(false);
  }, []);

  return { is_recording, audio_blob, start_recording, stop_recording, analyser_node };
}