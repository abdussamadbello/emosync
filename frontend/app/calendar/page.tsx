"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, CalendarDays, Plus, X, Trash2 } from "lucide-react";
import { get_token, get_profile } from "@/lib/api";
import {
  list_calendar_events,
  create_calendar_event,
  delete_calendar_event,
  type CalendarEvent,
} from "@/lib/calendar-api";

// Color coding by event type
const EVENT_COLORS: Record<string, string> = {
  anniversary: "bg-purple-500",
  birthday: "bg-blue-500",
  therapy: "bg-teal-500",
  trigger: "bg-red-500",
  milestone: "bg-green-500",
  holiday: "bg-orange-500",
  personal: "bg-gray-400",
};

const EVENT_BADGE_COLORS: Record<string, string> = {
  anniversary: "bg-purple-500/10 text-purple-700 border-purple-200",
  birthday: "bg-blue-500/10 text-blue-700 border-blue-200",
  therapy: "bg-teal-500/10 text-teal-700 border-teal-200",
  trigger: "bg-red-500/10 text-red-700 border-red-200",
  milestone: "bg-green-500/10 text-green-700 border-green-200",
  holiday: "bg-orange-500/10 text-orange-700 border-orange-200",
  personal: "bg-gray-500/10 text-gray-700 border-gray-200",
};

const EVENT_TYPES = ["anniversary", "birthday", "therapy", "trigger", "milestone", "holiday", "personal"];
const RECURRENCE_OPTIONS = ["none", "yearly", "monthly", "weekly"];
const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function pad_date(n: number): string {
  return String(n).padStart(2, "0");
}

function to_date_string(year: number, month: number, day: number): string {
  return `${year}-${pad_date(month + 1)}-${pad_date(day)}`;
}

function format_display_date(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

interface EventFormState {
  title: string;
  date: string;
  event_type: string;
  recurrence: string;
  notes: string;
  notify_agent: boolean;
}

const DEFAULT_FORM: EventFormState = {
  title: "",
  date: "",
  event_type: "personal",
  recurrence: "none",
  notes: "",
  notify_agent: false,
};

export default function CalendarPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [is_loading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const today = new Date();
  const [view_year, setViewYear] = useState(today.getFullYear());
  const [view_month, setViewMonth] = useState(today.getMonth()); // 0-indexed

  const [selected_date, setSelectedDate] = useState<string | null>(null);
  const [show_form, setShowForm] = useState(false);
  const [form, setForm] = useState<EventFormState>({ ...DEFAULT_FORM });
  const [is_submitting, setIsSubmitting] = useState(false);
  const [deleting_id, setDeletingId] = useState<string | null>(null);

  const load_events = useCallback(
    async (t: string, year: number, month: number) => {
      setIsLoading(true);
      setError("");
      const from_date = `${year}-${pad_date(month + 1)}-01`;
      const last_day = new Date(year, month + 1, 0).getDate();
      const to_date = `${year}-${pad_date(month + 1)}-${pad_date(last_day)}`;
      try {
        const data = await list_calendar_events(t, { from_date, to_date });
        setEvents(data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load events.");
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    const t = get_token();
    if (!t) {
      router.replace("/auth/login");
      return;
    }
    setToken(t);
    get_profile(t)
      .then((profile) => {
        if (!profile.onboarding_completed) {
          router.replace("/onboarding");
          return;
        }
        load_events(t, view_year, view_month);
      })
      .catch(() => router.replace("/auth/login"));
  }, [router, view_year, view_month, load_events]);

  function go_prev_month() {
    if (view_month === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
    setSelectedDate(null);
  }

  function go_next_month() {
    if (view_month === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
    setSelectedDate(null);
  }

  function open_form_for_date(date_str: string) {
    setForm({ ...DEFAULT_FORM, date: date_str });
    setShowForm(true);
    setError("");
  }

  function close_form() {
    setShowForm(false);
    setForm({ ...DEFAULT_FORM });
    setError("");
  }

  async function handle_create_event() {
    if (!form.title.trim()) {
      setError("Event title is required.");
      return;
    }
    if (!form.date) {
      setError("Event date is required.");
      return;
    }
    setIsSubmitting(true);
    setError("");
    try {
      const new_event = await create_calendar_event(token, {
        title: form.title.trim(),
        date: form.date,
        event_type: form.event_type,
        recurrence: form.recurrence !== "none" ? form.recurrence : undefined,
        notes: form.notes.trim() || undefined,
        notify_agent: form.notify_agent,
      });
      setEvents((prev) => [...prev, new_event]);
      close_form();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create event.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handle_delete_event(id: string) {
    setDeletingId(id);
    try {
      await delete_calendar_event(token, id);
      setEvents((prev) => prev.filter((e) => e.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete event.");
    } finally {
      setDeletingId(null);
    }
  }

  // Build calendar grid
  const first_day_of_month = new Date(view_year, view_month, 1).getDay(); // 0=Sun
  const days_in_month = new Date(view_year, view_month + 1, 0).getDate();

  // Map date string -> events for quick lookup
  const events_by_date: Record<string, CalendarEvent[]> = {};
  for (const ev of events) {
    const day = ev.date.slice(0, 10); // YYYY-MM-DD
    if (!events_by_date[day]) events_by_date[day] = [];
    events_by_date[day].push(ev);
  }

  const selected_events = selected_date ? (events_by_date[selected_date] ?? []) : [];

  const today_str = to_date_string(today.getFullYear(), today.getMonth(), today.getDate());

  // Grid cells: leading empty + day cells
  const grid_cells: Array<{ day: number | null; date_str: string | null }> = [];
  for (let i = 0; i < first_day_of_month; i++) {
    grid_cells.push({ day: null, date_str: null });
  }
  for (let d = 1; d <= days_in_month; d++) {
    grid_cells.push({ day: d, date_str: to_date_string(view_year, view_month, d) });
  }

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <CalendarDays className="size-5 text-primary" />
            <h1 className="text-xl font-semibold tracking-tight">Calendar</h1>
          </div>
          <Button
            size="sm"
            onClick={() => {
              const d = selected_date ?? today_str;
              open_form_for_date(d);
            }}
          >
            <Plus className="mr-1.5 size-4" />
            Add Event
          </Button>
        </div>

        {error && (
          <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {error}
          </p>
        )}

        {/* Month navigation */}
        <div className="mb-4 flex items-center justify-between">
          <button
            onClick={go_prev_month}
            className="rounded-lg border border-border p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <ChevronLeft className="size-4" />
          </button>
          <h2 className="text-base font-semibold">
            {MONTH_NAMES[view_month]} {view_year}
          </h2>
          <button
            onClick={go_next_month}
            className="rounded-lg border border-border p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>

        {/* Calendar grid */}
        <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
          {/* Day name headers */}
          <div className="grid grid-cols-7 border-b border-border">
            {DAY_NAMES.map((d) => (
              <div
                key={d}
                className="py-2 text-center text-xs font-medium text-muted-foreground"
              >
                {d}
              </div>
            ))}
          </div>

          {/* Grid */}
          <div className="grid grid-cols-7">
            {grid_cells.map((cell, idx) => {
              if (cell.day === null) {
                return (
                  <div
                    key={`empty-${idx}`}
                    className="min-h-[56px] border-b border-r border-border bg-muted/20 last:border-r-0"
                  />
                );
              }
              const date_str = cell.date_str!;
              const cell_events = events_by_date[date_str] ?? [];
              const is_today = date_str === today_str;
              const is_selected = date_str === selected_date;

              return (
                <button
                  key={date_str}
                  onClick={() => setSelectedDate(is_selected ? null : date_str)}
                  className={`relative min-h-[56px] border-b border-r border-border p-1.5 text-left transition-colors last:border-r-0 hover:bg-muted/50 ${
                    is_selected ? "bg-primary/5 ring-1 ring-inset ring-primary/40" : ""
                  } ${idx % 7 === 6 ? "border-r-0" : ""}`}
                >
                  <span
                    className={`flex size-6 items-center justify-center rounded-full text-xs font-medium ${
                      is_today
                        ? "bg-primary text-primary-foreground"
                        : "text-foreground"
                    }`}
                  >
                    {cell.day}
                  </span>
                  {/* Event dots */}
                  {cell_events.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-0.5">
                      {cell_events.slice(0, 3).map((ev) => (
                        <span
                          key={ev.id}
                          className={`size-1.5 rounded-full ${EVENT_COLORS[ev.event_type] ?? "bg-gray-400"}`}
                        />
                      ))}
                      {cell_events.length > 3 && (
                        <span className="text-[9px] text-muted-foreground">
                          +{cell_events.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Legend */}
        <div className="mt-3 flex flex-wrap gap-3">
          {EVENT_TYPES.map((type) => (
            <div key={type} className="flex items-center gap-1.5">
              <span className={`size-2 rounded-full ${EVENT_COLORS[type]}`} />
              <span className="text-xs text-muted-foreground capitalize">{type}</span>
            </div>
          ))}
        </div>

        {/* Selected date panel */}
        {selected_date && (
          <div className="mt-5 rounded-xl border border-border bg-card p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">{format_display_date(selected_date)}</h3>
              <Button
                size="sm"
                variant="outline"
                onClick={() => open_form_for_date(selected_date)}
                className="gap-1.5 text-xs"
              >
                <Plus className="size-3.5" />
                Add
              </Button>
            </div>
            {selected_events.length === 0 ? (
              <p className="text-xs text-muted-foreground">No events on this day.</p>
            ) : (
              <div className="flex flex-col gap-2">
                {selected_events.map((ev) => (
                  <div
                    key={ev.id}
                    className="flex items-start justify-between gap-3 rounded-lg border border-border p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium text-foreground">{ev.title}</p>
                        <span
                          className={`rounded-full border px-2 py-0.5 text-xs capitalize ${
                            EVENT_BADGE_COLORS[ev.event_type] ?? "bg-muted text-muted-foreground"
                          }`}
                        >
                          {ev.event_type}
                        </span>
                        {ev.recurrence && ev.recurrence !== "none" && (
                          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground capitalize">
                            {ev.recurrence}
                          </span>
                        )}
                      </div>
                      {ev.notes && (
                        <p className="mt-1 text-xs text-muted-foreground">{ev.notes}</p>
                      )}
                      {ev.notify_agent && (
                        <p className="mt-1 text-xs text-primary">AI will be aware of this event</p>
                      )}
                    </div>
                    <button
                      onClick={() => handle_delete_event(ev.id)}
                      disabled={deleting_id === ev.id}
                      className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                      title="Delete event"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Add event modal/form */}
        {show_form && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
            <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-base font-semibold">Add Calendar Event</h2>
                <button
                  onClick={close_form}
                  className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <X className="size-4" />
                </button>
              </div>

              {error && (
                <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  {error}
                </p>
              )}

              <div className="flex flex-col gap-4">
                {/* Title */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium">Title *</label>
                  <input
                    type="text"
                    value={form.title}
                    onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                    placeholder="Event title…"
                    className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
                  />
                </div>

                {/* Date */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium">Date *</label>
                  <input
                    type="date"
                    value={form.date}
                    onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                    className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
                  />
                </div>

                {/* Event type */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium">Type</label>
                  <select
                    value={form.event_type}
                    onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value }))}
                    className="rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
                  >
                    {EVENT_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t.charAt(0).toUpperCase() + t.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Recurrence */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium">Recurrence</label>
                  <select
                    value={form.recurrence}
                    onChange={(e) => setForm((f) => ({ ...f, recurrence: e.target.value }))}
                    className="rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
                  >
                    {RECURRENCE_OPTIONS.map((r) => (
                      <option key={r} value={r}>
                        {r.charAt(0).toUpperCase() + r.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Notes */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium">
                    Notes <span className="text-muted-foreground">(optional)</span>
                  </label>
                  <textarea
                    value={form.notes}
                    onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                    placeholder="Any notes about this event…"
                    rows={3}
                    className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30 resize-none"
                  />
                </div>

                {/* Notify agent toggle */}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Let AI know</p>
                    <p className="text-xs text-muted-foreground">
                      The grief coach will be aware of this event
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, notify_agent: !f.notify_agent }))}
                    className={`relative h-6 w-11 rounded-full transition-colors ${
                      form.notify_agent ? "bg-primary" : "bg-muted"
                    }`}
                  >
                    <span
                      className={`absolute left-0.5 top-0.5 size-5 rounded-full bg-white transition-transform ${
                        form.notify_agent ? "translate-x-5" : ""
                      }`}
                    />
                  </button>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-1">
                  <Button variant="outline" onClick={close_form} className="flex-1" disabled={is_submitting}>
                    Cancel
                  </Button>
                  <Button onClick={handle_create_event} disabled={is_submitting} className="flex-1">
                    {is_submitting ? "Saving…" : "Add Event"}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {is_loading && (
          <p className="mt-4 text-center text-xs text-muted-foreground">Loading events…</p>
        )}
      </div>
    </div>
  );
}
