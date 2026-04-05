"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, MessageSquare, BookOpen, Calendar, FileText } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { list_conversations, get_token } from "@/lib/api";
import { list_journal_entries } from "@/lib/journal-api";
import { list_calendar_events } from "@/lib/calendar-api";

interface SearchResult {
  id: string;
  title: string;
  type: "conversation" | "journal" | "calendar";
  href: string;
  preview?: string;
}

interface SearchModalProps {
  open: boolean;
  on_open_change: (open: boolean) => void;
}

export function SearchModal({ open, on_open_change }: SearchModalProps) {
  const router = useRouter();
  const [query, set_query] = useState("");
  const [results, set_results] = useState<SearchResult[]>([]);
  const [is_searching, set_is_searching] = useState(false);
  const input_ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && input_ref.current) {
      input_ref.current.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!query.trim()) {
      set_results([]);
      return;
    }

    set_is_searching(true);
    const timeout = setTimeout(async () => {
      const token = get_token();
      if (!token) {
        set_is_searching(false);
        return;
      }

      const q = query.toLowerCase();
      const all_results: SearchResult[] = [];

      try {
        const conversations = await list_conversations(token);
        const matched_convs = conversations.filter(
          (c) =>
            c.title?.toLowerCase().includes(q) ||
            c.id.toLowerCase().includes(q)
        );
        all_results.push(
          ...matched_convs.map((c) => ({
            id: c.id,
            title: c.title || c.id.slice(0, 8),
            type: "conversation" as const,
            href: `/c/${c.id}`,
          }))
        );
      } catch {
        // ignore
      }

      try {
        const entries = await list_journal_entries(token);
        const matched_entries = entries.filter(
          (e) =>
            e.title?.toLowerCase().includes(q) ||
            e.content.toLowerCase().includes(q)
        );
        all_results.push(
          ...matched_entries.map((e) => ({
            id: e.id,
            title: e.title || "Untitled entry",
            type: "journal" as const,
            href: `/journal/${e.id}`,
            preview: e.content.slice(0, 80),
          }))
        );
      } catch {
        // ignore
      }

      try {
        const events = await list_calendar_events(token);
        const matched_events = events.filter(
            (ev) =>
              ev.title.toLowerCase().includes(q) ||
              (ev.notes && ev.notes.toLowerCase().includes(q))
          );
          all_results.push(
            ...matched_events.map((ev) => ({
              id: ev.id,
              title: ev.title,
              type: "calendar" as const,
              href: "/calendar",
              preview: ev.notes?.slice(0, 80),
            }))
        );
      } catch {
        // ignore
      }

      set_results(all_results);
      set_is_searching(false);
    }, 300);

    return () => clearTimeout(timeout);
  }, [query]);

  function handle_select(result: SearchResult) {
    on_open_change(false);
    set_query("");
    set_results([]);
    router.push(result.href);
  }

  const type_icon = (type: SearchResult["type"]) => {
    switch (type) {
      case "conversation":
        return <MessageSquare className="size-4 shrink-0 text-muted-foreground" />;
      case "journal":
        return <BookOpen className="size-4 shrink-0 text-muted-foreground" />;
      case "calendar":
        return <Calendar className="size-4 shrink-0 text-muted-foreground" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={on_open_change}>
      <DialogContent className="max-w-xl p-0 gap-0">
        <DialogHeader className="px-6 pt-6 pb-0">
          <DialogTitle className="text-lg font-semibold">Search</DialogTitle>
        </DialogHeader>

        {/* Search input */}
        <div className="px-6 py-4">
          <div className="flex items-center gap-3 rounded-xl border border-input bg-muted/40 px-4 py-2.5 focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/25">
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <input
              ref={input_ref}
              type="text"
              value={query}
              onChange={(e) => set_query(e.target.value)}
              placeholder="Search conversations, journal entries, events..."
              className="flex-1 bg-transparent text-[0.9375rem] outline-none placeholder:text-muted-foreground/60"
            />
          </div>
        </div>

        {/* Results */}
        <div className="max-h-72 overflow-y-auto border-t border-border">
          {is_searching && (
            <div className="flex items-center justify-center py-8">
              <div className="flex items-center gap-1.5">
                <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:0ms]" />
                <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:150ms]" />
                <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:300ms]" />
              </div>
            </div>
          )}

          {!is_searching && query.trim() && results.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8">
              <Search className="size-8 text-muted-foreground/30 mb-2" />
              <p className="text-sm text-muted-foreground">No results found</p>
              <p className="text-xs text-muted-foreground/60 mt-1">
                Try a different search term
              </p>
            </div>
          )}

          {!is_searching && !query.trim() && (
            <div className="flex flex-col items-center justify-center py-8">
              <Search className="size-8 text-muted-foreground/30 mb-2" />
              <p className="text-sm text-muted-foreground">
                Type to search conversations, journal entries, and events
              </p>
            </div>
          )}

          {!is_searching && results.length > 0 && (
            <div className="py-2">
              {results.map((result) => (
                <button
                  key={`${result.type}-${result.id}`}
                  onClick={() => handle_select(result)}
                  className="w-full flex items-start gap-3 px-6 py-3 text-left hover:bg-muted/60 transition-colors"
                >
                  {type_icon(result.type)}
                  <div className="min-w-0 flex-1">
                    <p className="text-[0.9375rem] font-medium text-foreground truncate">
                      {result.title}
                    </p>
                    {result.preview && (
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                        {result.preview}
                      </p>
                    )}
                  </div>
                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground/60 shrink-0 mt-0.5">
                    {result.type}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
