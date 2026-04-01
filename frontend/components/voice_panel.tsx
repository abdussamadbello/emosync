"use client";

import { Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { VoiceChatStatus } from "@/hooks/use_voice_chat";

interface VoicePanelProps {
  status: VoiceChatStatus;
  interim_transcript: string;
  on_end: () => void;
}

const STATUS_LABEL: Record<VoiceChatStatus, string> = {
  disconnected: "Starting…",
  connecting:   "Connecting…",
  listening:    "Listening…",
  processing:   "Processing…",
  speaking:     "Speaking…",
  error:        "Error",
};

const STATUS_DOT: Record<VoiceChatStatus, string> = {
  disconnected: "bg-muted-foreground/40",
  connecting:   "animate-pulse bg-amber-400",
  listening:    "animate-pulse bg-green-500",
  processing:   "animate-pulse bg-amber-500",
  speaking:     "animate-pulse bg-blue-500",
  error:        "bg-destructive",
};

/**
 * Voice mode input area — rendered in place of the text input while a voice
 * WebSocket session is active. Shows the current pipeline status and a button
 * to end the session.
 */
export function VoicePanel({ status, interim_transcript, on_end }: VoicePanelProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-2">
      {/* Status pill */}
      <div className="flex items-center gap-2.5 rounded-full border border-border bg-muted/50 px-4 py-1.5">
        <span className={`size-2 rounded-full ${STATUS_DOT[status]}`} />
        <span className="text-sm text-muted-foreground">
          {STATUS_LABEL[status]}
        </span>
      </div>

      {/* Live interim transcript */}
      {interim_transcript && (
        <p className="max-w-xs truncate text-center text-xs italic text-muted-foreground">
          &ldquo;{interim_transcript}&rdquo;
        </p>
      )}

      {/* End session */}
      <Button
        variant="destructive"
        size="sm"
        onClick={on_end}
        className="gap-2 px-5"
      >
        <Square className="size-3 fill-current" />
        End Voice Chat
      </Button>
    </div>
  );
}
