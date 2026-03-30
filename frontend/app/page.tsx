"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Sparkles, Send, Mic, MicOff, Moon, Sun, ArrowRight } from "lucide-react";
import { useTheme } from "next-themes";
import { use_audio_recorder } from "@/hooks/use-audio-recorder";
import { mock_speech_to_text, mock_text_to_speech } from "@/lib/mock-audio-service";
import { Sidebar } from "@/components/sidebar";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  is_voice?: boolean;
}

const DEMO_RESPONSES: string[] = [
  "That's completely valid. Thank you for sharing that with me. Can you tell me more about what's been on your mind?",
  "I hear you. It sounds like you're navigating some complex emotions right now. What would feel most supportive for you?",
  "It takes courage to express how you feel. Let's explore that together \u2014 what do you think triggered this feeling?",
  "I appreciate you opening up. Remember, every emotion carries valuable information. What does this feeling tell you about what matters to you?",
  "That makes a lot of sense. Emotional awareness is a powerful first step. Would you like to try a quick grounding exercise together?",
];

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sidebar_open, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const responseIndexRef = useRef(0);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const { is_recording, audio_blob, start_recording, stop_recording } =
    use_audio_recorder();

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  function handle_send() {
    const trimmed = input.trim();
    if (!trimmed || isTyping) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      const response =
        DEMO_RESPONSES[responseIndexRef.current % DEMO_RESPONSES.length];
      responseIndexRef.current += 1;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response },
      ]);
      setIsTyping(false);
    }, 1200);
  }

  function handle_key_down(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handle_send();
    }
  }

  async function handle_voice_toggle() {
    if (is_recording) {
      stop_recording();
    } else {
      await start_recording();
    }
  }

  useEffect(() => {
    if (!audio_blob) return;

    async function process_voice_message() {
      setIsTyping(true);
      const transcription = await mock_speech_to_text(audio_blob!);

      setMessages((prev) => [
        ...prev,
        { role: "user", content: transcription, is_voice: true },
      ]);

      const response =
        DEMO_RESPONSES[responseIndexRef.current % DEMO_RESPONSES.length];
      responseIndexRef.current += 1;

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response, is_voice: true },
      ]);
      setIsTyping(false);

      await mock_text_to_speech(response);
    }

    const url = URL.createObjectURL(audio_blob!);
    const a = document.createElement("a");
    a.href = url;
    a.download = `emosync-recording-${Date.now()}.webm`;
    a.click();
    URL.revokeObjectURL(url);

    process_voice_message();
  }, [audio_blob]);

  const has_messages = messages.length > 0 || isTyping;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <Sidebar
        open={sidebar_open}
        on_toggle={() => setSidebarOpen((v) => !v)}
        is_logged_in={false}
      />

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center justify-end gap-3 border-b border-border/40 bg-background/80 px-4 backdrop-blur-md">
          <Button variant="outline" size="sm" asChild>
            <Link href="/auth/login">Login</Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/auth/register">
              Get Started
              <ArrowRight data-icon="inline-end" className="size-3.5" />
            </Link>
          </Button>
          {mounted && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              <Sun className="size-4 rotate-0 scale-100 transition-transform dark:rotate-90 dark:scale-0" />
              <Moon className="absolute size-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
            </Button>
          )}
        </header>

        {/* Chat panel */}
        <main className="flex flex-1 flex-col overflow-hidden p-4">
          <div className="flex flex-1 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm">
            {/* Messages / welcome area */}
            <div className="relative flex flex-1 flex-col overflow-y-auto">
              {!has_messages && (
                <div className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
                  {/* Breathing orb animation */}
                  <div className="relative flex items-center justify-center">
                    <div className="absolute size-28 animate-pulse rounded-full bg-primary/10 blur-xl" />
                    <div className="absolute size-20 animate-[pulse_3s_ease-in-out_infinite] rounded-full bg-primary/15 blur-lg" />
                    <div className="relative flex size-16 items-center justify-center rounded-full border border-primary/20 bg-gradient-to-br from-primary/10 to-primary/5">
                      <Sparkles className="size-7 animate-[spin_6s_linear_infinite] text-primary/70" />
                    </div>
                    <div className="absolute size-32 animate-[spin_8s_linear_infinite]">
                      <span className="absolute top-0 left-1/2 size-1.5 -translate-x-1/2 rounded-full bg-primary/40" />
                    </div>
                    <div className="absolute size-36 animate-[spin_12s_linear_infinite_reverse]">
                      <span className="absolute top-0 left-1/2 size-1 -translate-x-1/2 rounded-full bg-primary/30" />
                    </div>
                    <div className="absolute size-40 animate-[spin_10s_linear_infinite]">
                      <span className="absolute bottom-0 left-1/2 size-1.5 -translate-x-1/2 rounded-full bg-primary/20" />
                    </div>
                  </div>

                  <div className="text-center">
                    <h2 className="text-xl font-semibold tracking-tight">
                      Welcome to EmoSync
                    </h2>
                    <p className="mt-1.5 text-sm text-muted-foreground">
                      Your safe space for emotional wellness
                    </p>
                  </div>
                </div>
              )}

              {has_messages && (
                <div className="flex flex-col gap-3 p-4">
                  {messages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                          msg.role === "user"
                            ? "rounded-br-md bg-primary text-primary-foreground"
                            : "rounded-bl-md bg-muted text-foreground"
                        }`}
                      >
                        {msg.role === "assistant" && (
                          <>
                            <Sparkles className="mb-0.5 inline-block size-3.5 text-primary" />{" "}
                          </>
                        )}
                        {msg.content}
                        {msg.is_voice && (
                          <Mic className="ml-1.5 mb-0.5 inline-block size-3 opacity-50" />
                        )}
                      </div>
                    </div>
                  ))}

                  {isTyping && (
                    <div className="flex justify-start">
                      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md bg-muted px-4 py-3">
                        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:0ms]" />
                        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:150ms]" />
                        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:300ms]" />
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Input bar */}
            <div className="border-t border-border bg-background px-3 pt-3 pb-1">
              <p className="mb-2 text-center text-[11px] text-muted-foreground/70">
                EmoSync can make mistakes. Always seek professional help for serious mental health concerns.
              </p>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handle_key_down}
                  placeholder={
                    is_recording ? "Listening..." : "How are you feeling today?"
                  }
                  disabled={is_recording || isTyping}
                  className="flex-1 rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50"
                />
                <Button
                  size="icon"
                  variant={is_recording ? "destructive" : "outline"}
                  onClick={handle_voice_toggle}
                  disabled={isTyping}
                  title={is_recording ? "Stop recording" : "Start voice input"}
                  className={is_recording ? "animate-pulse" : ""}
                >
                  {is_recording ? (
                    <MicOff className="size-4" />
                  ) : (
                    <Mic className="size-4" />
                  )}
                </Button>
                <Button
                  size="icon"
                  onClick={handle_send}
                  disabled={!input.trim() || isTyping || is_recording}
                >
                  <Send className="size-4" />
                </Button>
              </div>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-border/40 py-3 text-center text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} EmoSync. All rights reserved.
        </footer>
      </div>
    </div>
  );
}
