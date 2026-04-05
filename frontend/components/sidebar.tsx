"use client";

import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  Plus,
  Search,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  CreditCard,
  Trash2,
  BookOpen,
  Calendar,
} from "lucide-react";
import type { ConversationOut } from "@/lib/api";

interface SidebarProps {
  /** Whether the sidebar is expanded */
  open: boolean;
  /** Callback to toggle open/closed */
  on_toggle: () => void;
  /** Whether a user is currently logged in */
  is_logged_in?: boolean;
  /** Called when the user clicks "New Chat" */
  on_new_chat?: () => void;
  /** Called when the user deletes a conversation */
  on_delete_chat?: (conversation_id: string) => void;
  /** List of conversations to display under "Your Chats" */
  conversations?: ConversationOut[];
  /** Id of the currently active conversation (highlighted) */
  active_conversation_id?: string | null;
}

/**
 * Returns a short display label for a conversation.
 * Uses title if set, otherwise falls back to the first 8 chars of the id.
 */
function conversation_label(conv: ConversationOut): string {
  return conv.title?.trim() || conv.id.slice(0, 8);
}

/**
 * Collapsible sidebar with navigation links and real conversation list.
 */
export function Sidebar({
  open,
  on_toggle,
  is_logged_in = false,
  on_new_chat,
  on_delete_chat,
  conversations = [],
  active_conversation_id,
}: SidebarProps) {
  return (
    <aside
      className={`relative flex h-full flex-col border-r border-border bg-sidebar transition-all duration-300 ease-in-out ${
        open ? "w-64" : "w-14"
      }`}
    >
      {/* Toggle button */}
      <button
        onClick={on_toggle}
        aria-label={open ? "Collapse sidebar" : "Expand sidebar"}
        className="absolute -right-3 top-5 z-10 flex size-6 items-center justify-center rounded-full border border-border bg-background text-muted-foreground shadow-sm transition-colors hover:bg-muted hover:text-foreground"
      >
        {open ? <ChevronLeft className="size-3.5" /> : <ChevronRight className="size-3.5" />}
      </button>

      {/* Logo */}
      <div className="flex h-14 items-center border-b border-border px-3">
        <Link href="/" className="flex min-w-0 items-center gap-2.5">
          <Image
            src="/logo.png"
            alt="EmoSync"
            width={28}
            height={28}
            className="shrink-0 rounded-sm"
          />
          {open && (
            <span className="truncate text-base font-semibold tracking-tight">
              EmoSync
            </span>
          )}
        </Link>
      </div>

      {/* Nav links */}
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
        {/* New Chat */}
        <Button
          variant="ghost"
          className={`w-full justify-start gap-3 ${open ? "px-3" : "px-0 justify-center"}`}
          onClick={on_new_chat}
        >
          <Plus className="size-4 shrink-0" />
          {open && <span className="truncate">New Chat</span>}
        </Button>

        {/* Search */}
        <Button
          variant="ghost"
          className={`w-full justify-start gap-3 ${open ? "px-3" : "px-0 justify-center"}`}
          asChild
        >
          <Link href="/search">
            <Search className="size-4 shrink-0" />
            {open && <span className="truncate">Search Chats</span>}
          </Link>
        </Button>

        {/* Past chats — expanded, logged in */}
        {is_logged_in && open && (
          <div className="mt-4">
            <p className="mb-1 px-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Your Chats
            </p>
            <div className="flex flex-col gap-0.5">
              {conversations.length === 0 ? (
                <p className="px-3 text-xs text-muted-foreground">No chats yet</p>
              ) : (
                conversations.map((conv) => {
                  const is_active = conv.id === active_conversation_id;
                  return (
                    <div
                      key={conv.id}
                      className="group relative flex items-center"
                    >
                      <Button
                        variant={is_active ? "secondary" : "ghost"}
                        className="w-full justify-start gap-3 px-3 pr-8 text-sm"
                        asChild
                      >
                        <Link href={`/c/${conv.id}`}>
                          <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                          <span className="truncate">{conversation_label(conv)}</span>
                        </Link>
                      </Button>
                      {on_delete_chat && (
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            on_delete_chat(conv.id);
                          }}
                          title="Delete chat"
                          className="absolute right-1.5 flex size-6 items-center justify-center rounded opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Collapsed icon-only past chats */}
        {is_logged_in && !open && (
          <Button
            variant="ghost"
            className="w-full justify-center px-0"
            title="Your Chats"
          >
            <MessageSquare className="size-4 shrink-0" />
          </Button>
        )}

        {/* Journal & Calendar links */}
        <Button
          variant="ghost"
          className={`w-full justify-start gap-3 ${open ? "px-3" : "px-0 justify-center"}`}
          title="Journal"
          asChild
        >
          <Link href="/journal">
            <BookOpen className="size-4 shrink-0" />
            {open && <span className="truncate">Journal</span>}
          </Link>
        </Button>

        <Button
          variant="ghost"
          className={`w-full justify-start gap-3 ${open ? "px-3" : "px-0 justify-center"}`}
          title="Calendar"
          asChild
        >
          <Link href="/calendar">
            <Calendar className="size-4 shrink-0" />
            {open && <span className="truncate">Calendar</span>}
          </Link>
        </Button>
      </nav>

      {/* Bottom links */}
      <div className="flex flex-col gap-1 border-t border-border p-2">
        <Button
          variant="ghost"
          className={`w-full justify-start gap-3 ${open ? "px-3" : "px-0 justify-center"}`}
          title="Help"
          asChild
        >
          <Link href="/help">
            <HelpCircle className="size-4 shrink-0" />
            {open && <span className="truncate">Help</span>}
          </Link>
        </Button>

        <Button
          variant="ghost"
          className={`w-full justify-start gap-3 ${open ? "px-3" : "px-0 justify-center"}`}
          title="Subscription"
          asChild
        >
          <Link href="/subscription">
            <CreditCard className="size-4 shrink-0" />
            {open && <span className="truncate">Subscription</span>}
          </Link>
        </Button>
      </div>
    </aside>
  );
}
