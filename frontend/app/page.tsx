"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Sparkles, Send, Mic, Moon, Sun, ArrowRight, LogOut, User } from "lucide-react";
import { useTheme } from "next-themes";
import { Sidebar } from "@/components/sidebar";
import { VoicePanel } from "@/components/voice_panel";
import { use_voice_chat } from "@/hooks/use_voice_chat";
import {
  get_token,
  clear_auth,
  create_conversation,
  stream_message,
  list_conversations,
  list_messages,
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

export default function Home() {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // ── Session ───────────────────────────────────────────────────────────────
  const [is_session_loading, setIsSessionLoading] = useState(true);
  const [display_name, setDisplayName] = useState<string | null>(null);

  // ── Conversations ─────────────────────────────────────────────────────────
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [conversation_id, setConversationId] = useState<string | null>(null);

  // ── Messages ──────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [is_typing, setIsTyping] = useState(false);
  const [chat_error, setChatError] = useState<string | null>(null);
  const messages_end_ref = useRef<HTMLDivElement>(null);

  // ── Text input ────────────────────────────────────────────────────────────
  const [input, setInput] = useState("");

  // ── Sidebar ───────────────────────────────────────────────────────────────
  const [sidebar_open, setSidebarOpen] = useState(true);

  // ── Voice mode ────────────────────────────────────────────────────────────
  const [is_voice_mode, setIsVoiceMode] = useState(false);

  // Streaming assistant text from the voice hook — appended to the last bubble.
  const voice_assistant_bubble_ref = useRef<string>("");

  /**
   * Called by the voice hook for each incoming text delta.
   * Appends the fragment to the current assistant bubble in the message list.
   */
  const handle_voice_delta = useCallback((delta: string) => {
    voice_assistant_bubble_ref.current += delta;
    setMessages((prev) => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      if (last?.role === "assistant" && last.is_voice) {
        updated[updated.length - 1] = { ...last, content: last.content + delta };
        return updated;
      }
      // First delta for this turn: create the assistant bubble.
      return [...prev, { role: "assistant", content: delta, is_voice: true }];
    });
  }, []);

  /**
   * Called by the voice hook when a full turn is complete (text + audio done).
   */
  const handle_voice_message = useCallback((_full_text: string) => {
    voice_assistant_bubble_ref.current = "";
    setIsTyping(false);
  }, []);

  /**
   * Called by the voice hook when the user's STT utterance is finalised.
   * Adds the user message and an empty typing indicator.
   */
  const handle_user_transcript = useCallback((text: string) => {
    voice_assistant_bubble_ref.current = "";
    setIsTyping(true);
    setMessages((prev) => [...prev, { role: "user", content: text, is_voice: true }]);
  }, []);

  const voice = use_voice_chat({
    on_user_transcript: handle_user_transcript,
    on_assistant_message: handle_voice_message,
    on_assistant_delta: handle_voice_delta,
    on_error: (msg) => setChatError(msg),
  });

  // ── Bootstrap ─────────────────────────────────────────────────────────────
  useEffect(() => {
    setMounted(true);

    /**
     * Rehydrates the signed-in session from the backend so the UI does not
     * trust stale localStorage profile data.
     */
    async function bootstrap_session() {
      const token = get_token();
      if (!token) { setIsSessionLoading(false); return; }
      try {
        const user = await get_current_user(token);
        const name = user.display_name ?? user.email;
        save_display_name(name);
        setDisplayName(name);
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

  useEffect(() => {
    messages_end_ref.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, is_typing]);

  // ── Conversation helpers ──────────────────────────────────────────────────
  /**
   * Fetches all conversations for the current user and updates the sidebar.
   */
  async function load_conversations(token: string) {
    try {
      setConversations(await list_conversations(token));
    } catch { /* sidebar list stays empty */ }
  }

  /**
   * Lazily creates a backend conversation the first time the user sends a message.
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
   * Loads a past conversation and makes it the active one.
   */
  async function select_conversation(id: string) {
    const token = get_token();
    if (!token) return;
    setChatError(null);
    setConversationId(id);
    try {
      const history = await list_messages(token, id);
      setMessages(history.map((m) => ({ role: m.role as "user" | "assistant", content: m.content })));
    } catch {
      setChatError("Could not load conversation history.");
    }
  }

  /**
   * Clears auth state and redirects to the login page.
   */
  function handle_logout() {
    voice.disconnect();
    clear_auth();
    setDisplayName(null);
    setConversationId(null);
    setConversations([]);
    setMessages([]);
    setChatError(null);
    router.push("/auth/login");
  }

  // ── Text chat ─────────────────────────────────────────────────────────────
  /**
   * Removes an empty assistant placeholder bubble when a stream fails before
   * any content arrives.
   */
  function clear_pending_assistant_message() {
    setMessages((prev) => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      if (last?.role === "assistant" && !last.content.trim()) updated.pop();
      return updated;
    });
  }

  /**
   * Sends the typed message to the backend and streams the reply token-by-token
   * via SSE. Falls back to a demo response when the user is not logged in.
   */
  async function handle_send() {
    const trimmed = input.trim();
    if (!trimmed || is_typing) return;

    setChatError(null);
    const token = get_token();

    if (!token) {
      setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
      setInput("");
      setIsTyping(true);
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Please log in to start a real conversation with EmoSync." },
        ]);
        setIsTyping(false);
      }, 800);
      return;
    }

    setInput("");
    setIsTyping(true);

    const active_id = await ensure_active_conversation(token);
    if (!active_id) { setInput(trimmed); setIsTyping(false); return; }

    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed },
      { role: "assistant", content: "" },
    ]);

    try {
      const response = await stream_message(token, active_id, trimmed);
      for await (const evt of read_sse_stream(response)) {
        if (evt.event === "token") {
          const fragment = (evt.data.text as string) ?? "";
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.role === "assistant") {
              updated[updated.length - 1] = { ...last, content: last.content + fragment };
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
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to reach the server.";
      clear_pending_assistant_message();
      setChatError(msg);
      setIsTyping(false);
    }
  }

  function handle_key_down(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handle_send(); }
  }

  // ── Voice mode entry / exit ───────────────────────────────────────────────
  /**
   * Ensures a conversation exists, then opens the voice WebSocket and enters
   * voice mode.
   */
  async function enter_voice_mode() {
    const token = get_token();
    if (!token) { setChatError("Please log in to use voice chat."); return; }

    setChatError(null);
    const active_id = await ensure_active_conversation(token);
    if (!active_id) return;

    setIsVoiceMode(true);
    await voice.connect(active_id, token);
  }

  /**
   * Closes the voice WebSocket and returns to text input mode.
   */
  function exit_voice_mode() {
    voice.disconnect();
    setIsVoiceMode(false);
    setIsTyping(false);
  }

  const has_messages = messages.length > 0 || is_typing;

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
          exit_voice_mode();
          setMessages([]);
          setChatError(null);
          setConversationId(null);
        }}
      />

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center justify-end gap-3 border-b border-border/40 bg-background/80 px-4 backdrop-blur-md">
          {mounted && !is_session_loading && display_name && (
            <>
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <User className="size-3.5 shrink-0" />
                <span className="font-medium text-foreground">{display_name}</span>
              </span>
              <Button variant="outline" size="sm" onClick={handle_logout} className="gap-1.5">
                <LogOut className="size-3.5" />
                Sign Out
              </Button>
            </>
          )}
          {mounted && !is_session_loading && !display_name && (
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
          )}
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
                    <h2 className="text-xl font-semibold tracking-tight">Welcome to EmoSync</h2>
                    <p className="mt-1.5 text-sm text-muted-foreground">Your safe space for emotional wellness</p>
                  </div>
                </div>
              )}

              {has_messages && (
                <div className="flex flex-col gap-3 p-4">
                  {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                          msg.role === "user"
                            ? "rounded-br-md bg-primary text-primary-foreground"
                            : "rounded-bl-md bg-muted text-foreground"
                        }`}
                      >
                        {msg.role === "assistant" && (
                          <><Sparkles className="mb-0.5 inline-block size-3.5 text-primary" />{" "}</>
                        )}
                        {msg.content}
                        {msg.is_voice && (
                          <Mic className="ml-1.5 mb-0.5 inline-block size-3 opacity-50" />
                        )}
                      </div>
                    </div>
                  ))}

                  {is_typing && (
                    <div className="flex justify-start">
                      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md bg-muted px-4 py-3">
                        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:0ms]" />
                        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:150ms]" />
                        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:300ms]" />
                      </div>
                    </div>
                  )}
                  <div ref={messages_end_ref} />
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
                <VoicePanel
                  status={voice.status}
                  interim_transcript={voice.interim_transcript}
                  on_end={exit_voice_mode}
                />
              ) : (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handle_key_down}
                    placeholder="How are you feeling today?"
                    disabled={is_typing}
                    className="flex-1 rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                  <Button
                    size="icon"
                    variant="outline"
                    onClick={enter_voice_mode}
                    disabled={is_typing || !voice.is_stt_supported}
                    title={voice.is_stt_supported ? "Start voice chat" : "Voice chat requires Chrome or Edge"}
                  >
                    <Mic className="size-4" />
                  </Button>
                  <Button
                    size="icon"
                    onClick={handle_send}
                    disabled={!input.trim() || is_typing}
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
