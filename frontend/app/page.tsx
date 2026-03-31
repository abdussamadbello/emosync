"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Sparkles, Send, Mic, Moon, Sun, ArrowRight, LogOut, User, Square } from "lucide-react";
import { useTheme } from "next-themes";
import { use_audio_recorder } from "@/hooks/use-audio-recorder";
import { mock_speech_to_text, mock_text_to_speech } from "@/lib/mock-audio-service";
import { Sidebar } from "@/components/sidebar";
import {
  get_token,
  clear_auth,
  create_conversation, stream_message,
  list_conversations, list_messages,
  get_current_user,
  save_display_name,
  type ConversationOut,
} from "@/lib/api";
import { read_sse_stream } from "@/lib/sse";

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
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sidebar_open, setSidebarOpen] = useState(true);
  const [display_name, setDisplayName] = useState<string | null>(null);
  const [conversation_id, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [chat_error, setChatError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const responseIndexRef = useRef(0);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [is_session_loading, setIsSessionLoading] = useState(true);
  const [is_voice_mode, setIsVoiceMode] = useState(false);
  const [voice_status, setVoiceStatus] = useState<"listening" | "processing" | "speaking" | null>(null);
  const is_voice_mode_ref = useRef(false);
  const { is_recording, audio_blob, start_recording, stop_recording, analyser_node } =
    use_audio_recorder();

  useEffect(() => {
    setMounted(true);

    /**
     * Rehydrates the signed-in session from the backend so the UI does not
     * trust stale localStorage profile data.
     */
    async function bootstrap_session() {
      const token = get_token();
      if (!token) {
        setIsSessionLoading(false);
        return;
      }

      try {
        const user = await get_current_user(token);
        const next_display_name = user.display_name ?? user.email;
        save_display_name(next_display_name);
        setDisplayName(next_display_name);
        await load_conversations(token);
      } catch {
        clear_auth();
        setDisplayName(null);
        setConversationId(null);
        setConversations([]);
      } finally {
        setIsSessionLoading(false);
      }
    }

    void bootstrap_session();
  }, []);

  /**
   * Fetches all conversations for the current user and updates sidebar state.
   */
  async function load_conversations(token: string) {
    try {
      const data = await list_conversations(token);
      setConversations(data);
    } catch {
      // Non-critical — sidebar list just stays empty
    }
  }

  /**
   * Creates a backend conversation only when the user is about to send the
   * first real message in a new chat.
   */
  async function ensure_active_conversation(token: string): Promise<string | null> {
    if (conversation_id) return conversation_id;

    try {
      const conv = await create_conversation(token);
      setConversationId(conv.id);
      return conv.id;
    } catch {
      setChatError("Could not start a conversation. Please try again.");
      return null;
    }
  }

  /**
   * Loads a past conversation: sets it as active and fetches its message history.
   */
  async function select_conversation(id: string) {
    const token = get_token();
    if (!token) return;

    setChatError(null);
    setConversationId(id);

    try {
      const history = await list_messages(token, id);
      setMessages(
        history.map((m) => ({ role: m.role as "user" | "assistant", content: m.content }))
      );
    } catch {
      setChatError("Could not load conversation history.");
    }
  }

  /**
   * Clears auth data from localStorage and resets UI to logged-out state.
   */
  function handle_logout() {
    clear_auth();
    setDisplayName(null);
    setConversationId(null);
    setConversations([]);
    setMessages([]);
    setChatError(null);
    router.push("/auth/login");
  }

  /**
   * Enters continuous voice conversation mode: sets voice state, begins
   * recording, and hands control to the silence-detection and processing loop.
   */
  async function enter_voice_mode() {
    setChatError(null);
    is_voice_mode_ref.current = true;
    setIsVoiceMode(true);
    setVoiceStatus("listening");
    try {
      await start_recording();
    } catch {
      is_voice_mode_ref.current = false;
      setIsVoiceMode(false);
      setVoiceStatus(null);
      setChatError("Could not access your microphone. Please check permissions.");
    }
  }

  /**
   * Exits voice conversation mode, stops any active recording, and cancels
   * any in-progress TTS playback.
   */
  function exit_voice_mode() {
    is_voice_mode_ref.current = false;
    setIsVoiceMode(false);
    setVoiceStatus(null);
    stop_recording();
    speechSynthesis.cancel();
  }

  /**
   * Watches the audio analyser while in voice mode and automatically stops
   * recording after 1.8 s of silence (with a 600 ms warmup so the user has
   * time to start speaking before silence is measured).
   */
  useEffect(() => {
    if (!analyser_node || !is_voice_mode) return;

    const data = new Uint8Array(analyser_node.frequencyBinCount);
    const SILENCE_THRESHOLD = 10;
    const SILENCE_DURATION_MS = 1800;
    const WARMUP_MS = 600;
    const started_at = Date.now();
    let silence_start: number | null = null;

    const interval_id = setInterval(() => {
      if (!is_voice_mode_ref.current) {
        clearInterval(interval_id);
        return;
      }

      if (Date.now() - started_at < WARMUP_MS) return;

      analyser_node.getByteFrequencyData(data);
      const avg = data.reduce((a, b) => a + b, 0) / data.length;

      if (avg < SILENCE_THRESHOLD) {
        if (!silence_start) silence_start = Date.now();
        else if (Date.now() - silence_start > SILENCE_DURATION_MS) {
          clearInterval(interval_id);
          stop_recording();
        }
      } else {
        silence_start = null;
      }
    }, 100);

    return () => clearInterval(interval_id);
  }, [analyser_node, is_voice_mode, stop_recording]);

  /**
   * Removes the placeholder assistant bubble when the stream fails before any
   * content has been received.
   */
  function clear_pending_assistant_message() {
    setMessages((prev) => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      if (last?.role === "assistant" && !last.content.trim()) {
        updated.pop();
      }
      return updated;
    });
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  /**
   * Sends the user's message to the backend and streams the assistant's
   * response word-by-word via SSE, appending tokens to the UI in real time.
   * Falls back to the demo responses when the user is not logged in.
   */
  async function handle_send() {
    const trimmed = input.trim();
    if (!trimmed || isTyping) return;

    setChatError(null);
    const token = get_token();

    // Guest / unauthenticated: use demo responses
    if (!token) {
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
      return;
    }

    setInput("");
    setIsTyping(true);

    const active_conversation_id = await ensure_active_conversation(token);
    if (!active_conversation_id) {
      setInput(trimmed);
      setIsTyping(false);
      return;
    }

    // Authenticated: stream from backend
    // Add the user message plus an empty assistant bubble that we'll fill token-by-token
    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed },
      { role: "assistant", content: "" },
    ]);

    try {
      const response = await stream_message(token, active_conversation_id, trimmed);

      for await (const evt of read_sse_stream(response)) {
        if (evt.event === "token") {
          const fragment = (evt.data.text as string) ?? "";
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + fragment,
              };
            }
            return updated;
          });
        } else if (evt.event === "done") {
          setIsTyping(false);
          void load_conversations(token);
        } else if (evt.event === "error") {
          const msg = (evt.data.message as string) ?? "Assistant error";
          clear_pending_assistant_message();
          setChatError(msg);
          setIsTyping(false);
          void load_conversations(token);
        }
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to reach the server.";
      clear_pending_assistant_message();
      setChatError(msg);
      setIsTyping(false);
    }
  }

  function handle_key_down(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handle_send();
    }
  }

  /**
   * Processes a completed audio recording: transcribes it, shows messages,
   * speaks the response via TTS, then automatically restarts recording when
   * still in voice mode to continue the conversation loop.
   */
  useEffect(() => {
    if (!audio_blob) return;

    let cancelled = false;

    async function process_voice_turn() {
      if (!is_voice_mode_ref.current) return;

      setVoiceStatus("processing");
      setIsTyping(true);

      try {
        const transcription = await mock_speech_to_text(audio_blob!);
        if (cancelled) return;

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

        setVoiceStatus("speaking");
        await mock_text_to_speech(response);
        if (cancelled) return;

        if (is_voice_mode_ref.current) {
          setVoiceStatus("listening");
          await start_recording();
        } else {
          setVoiceStatus(null);
        }
      } catch {
        if (!cancelled) {
          setIsTyping(false);
          is_voice_mode_ref.current = false;
          setIsVoiceMode(false);
          setVoiceStatus(null);
          setChatError("Voice session ended unexpectedly. Please try again.");
          speechSynthesis.cancel();
        }
      }
    }

    void process_voice_turn();

    return () => {
      cancelled = true;
    };
  }, [audio_blob, start_recording]);

  const has_messages = messages.length > 0 || isTyping;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <Sidebar
        open={sidebar_open}
        on_toggle={() => setSidebarOpen((v) => !v)}
        is_logged_in={!is_session_loading && !!display_name}
        conversations={conversations}
        active_conversation_id={conversation_id}
        on_select_conversation={select_conversation}
        on_new_chat={() => {
          setMessages([]);
          setChatError(null);
          setConversationId(null);
        }}
      />

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center justify-end gap-3 border-b border-border/40 bg-background/80 px-4 backdrop-blur-md">
          {mounted && !is_session_loading && display_name ? (
            <>
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <User className="size-3.5 shrink-0" />
                <span className="font-medium text-foreground">{display_name}</span>
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={handle_logout}
                className="gap-1.5"
              >
                <LogOut className="size-3.5" />
                Sign Out
              </Button>
            </>
          ) : null}
          {mounted && !is_session_loading && !display_name ? (
            <>
              <Button variant="outline" size="sm" asChild>
                <Link href="/auth/login">Login</Link>
              </Button>
              <Button size="sm" asChild>
                <Link href="/auth/register">
                  Get Started
                  <ArrowRight data-icon="inline-end" className="size-3.5" />
                </Link>
              </Button>
            </>
          ) : null}
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
              {chat_error && (
                <p className="mb-2 rounded-lg bg-destructive/10 px-3 py-2 text-center text-xs text-destructive">
                  {chat_error}
                </p>
              )}
              <p className="mb-2 text-center text-[11px] text-muted-foreground/70">
                EmoSync can make mistakes. Always seek professional help for serious mental health concerns.
              </p>

              {is_voice_mode ? (
                /* Voice mode panel — replaces the text input while in session */
                <div className="flex flex-col items-center gap-3 py-2">
                  {/* Animated status pill */}
                  <div className="flex items-center gap-2.5 rounded-full border border-border bg-muted/50 px-4 py-1.5">
                    <span
                      className={`size-2 rounded-full ${
                        voice_status === "listening"
                          ? "animate-pulse bg-green-500"
                          : voice_status === "processing"
                          ? "animate-pulse bg-amber-500"
                          : voice_status === "speaking"
                          ? "animate-pulse bg-blue-500"
                          : "bg-muted-foreground/40"
                      }`}
                    />
                    <span className="text-sm text-muted-foreground">
                      {voice_status === "listening"
                        ? "Listening…"
                        : voice_status === "processing"
                        ? "Processing…"
                        : voice_status === "speaking"
                        ? "Speaking…"
                        : "Starting…"}
                    </span>
                  </div>

                  {/* End voice session */}
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={exit_voice_mode}
                    className="gap-2 px-5"
                  >
                    <Square className="size-3 fill-current" />
                    End Voice Chat
                  </Button>
                </div>
              ) : (
                /* Normal text input */
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handle_key_down}
                    placeholder="How are you feeling today?"
                    disabled={isTyping}
                    className="flex-1 rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                  <Button
                    size="icon"
                    variant="outline"
                    onClick={enter_voice_mode}
                    disabled={isTyping || is_recording}
                    title="Start voice chat"
                  >
                    <Mic className="size-4" />
                  </Button>
                  <Button
                    size="icon"
                    onClick={handle_send}
                    disabled={!input.trim() || isTyping || is_recording}
                  >
                    <Send className="size-4" />
                  </Button>
                </div>
              )}
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
