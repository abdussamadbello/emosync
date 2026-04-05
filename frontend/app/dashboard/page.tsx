"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  TrendingUp,
  Target,
  Calendar,
  BookOpen,
  MessageCircle,
} from "lucide-react";
import { get_token, get_profile } from "@/lib/api";
import { get_mood_trend, list_plans, type MoodTrend, type TreatmentPlan } from "@/lib/plan-api";
import { list_calendar_events, type CalendarEvent } from "@/lib/calendar-api";
import { list_journal_entries, type JournalEntry } from "@/lib/journal-api";

function format_date(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function to_iso_date(d: Date): string {
  return d.toISOString().split("T")[0];
}

export default function DashboardPage() {
  const router = useRouter();
  const [is_checking, setIsChecking] = useState(true);
  const [token, setToken] = useState("");

  const [mood, setMood] = useState<MoodTrend | null>(null);
  const [plans, setPlans] = useState<TreatmentPlan[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [journal, setJournal] = useState<JournalEntry[]>([]);

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
        setIsChecking(false);

        const today = new Date();
        const in_7 = new Date(today);
        in_7.setDate(today.getDate() + 7);

        Promise.allSettled([
          get_mood_trend(t).then(setMood),
          list_plans(t).then(setPlans),
          list_calendar_events(t, {
            from_date: to_iso_date(today),
            to_date: to_iso_date(in_7),
          }).then(setEvents),
          list_journal_entries(t).then(setJournal),
        ]);
      })
      .catch(() => {
        router.replace("/auth/login");
      });
  }, [router]);

  if (is_checking || !token) return null;

  const active_plan = plans.find((p) => p.status === "active") ?? plans[0] ?? null;
  const completed_goals = active_plan
    ? active_plan.goals.filter((g) => g.status === "completed").length
    : 0;
  const total_goals = active_plan ? active_plan.goals.length : 0;
  const next_target = active_plan?.goals
    .filter((g) => g.status !== "completed" && g.target_date)
    .sort((a, b) => (a.target_date! > b.target_date! ? 1 : -1))[0]?.target_date ?? null;

  const direction_icon =
    mood?.direction === "up" ? "↑" : mood?.direction === "down" ? "↓" : "→";
  const direction_color =
    mood?.direction === "up"
      ? "text-green-500"
      : mood?.direction === "down"
      ? "text-red-500"
      : "text-muted-foreground";

  const next_events = events.slice(0, 3);
  const recent_journal = journal.slice(0, 3);

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Here&apos;s a summary of your progress.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mood Trend */}
        <Link href="/plan" className="group">
          <div className="rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow group-hover:shadow-md h-full">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="size-4 text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">Mood Trend</span>
            </div>
            {mood ? (
              <div className="flex flex-col gap-1">
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold">
                    {mood.average.toFixed(1)}
                  </span>
                  <span className={`text-2xl font-bold ${direction_color}`}>
                    {direction_icon}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {mood.count} {mood.count === 1 ? "entry" : "entries"} over the last{" "}
                  {mood.period_days} days
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No mood data yet.</p>
            )}
          </div>
        </Link>

        {/* Treatment Plan */}
        <Link href="/plan" className="group">
          <div className="rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow group-hover:shadow-md h-full">
            <div className="flex items-center gap-2 mb-3">
              <Target className="size-4 text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">Treatment Plan</span>
            </div>
            {active_plan ? (
              <div className="flex flex-col gap-2">
                <p className="font-medium leading-snug">{active_plan.title}</p>
                {total_goals > 0 && (
                  <>
                    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${(completed_goals / total_goals) * 100}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {completed_goals} / {total_goals} goals completed
                    </p>
                  </>
                )}
                {next_target && (
                  <p className="text-xs text-muted-foreground">
                    Next target: {format_date(next_target)}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No active plan.</p>
            )}
          </div>
        </Link>

        {/* Upcoming Events */}
        <Link href="/calendar" className="group">
          <div className="rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow group-hover:shadow-md h-full">
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="size-4 text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">Upcoming Events</span>
            </div>
            {next_events.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {next_events.map((ev) => (
                  <li key={ev.id} className="flex items-center justify-between">
                    <span className="text-sm truncate max-w-[70%]">{ev.title}</span>
                    <span className="text-xs text-muted-foreground">{format_date(ev.date)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No upcoming events.</p>
            )}
          </div>
        </Link>

        {/* Recent Journal */}
        <Link href="/journal" className="group">
          <div className="rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow group-hover:shadow-md h-full">
            <div className="flex items-center gap-2 mb-3">
              <BookOpen className="size-4 text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">Recent Journal</span>
            </div>
            {recent_journal.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {recent_journal.map((entry) => (
                  <li key={entry.id} className="flex items-center justify-between">
                    <span className="text-sm truncate max-w-[70%]">
                      {entry.title ?? entry.content.slice(0, 40)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {format_date(entry.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No journal entries yet.</p>
            )}
          </div>
        </Link>
      </div>

      <div className="flex justify-center pt-2">
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
        >
          <MessageCircle className="size-5" />
          Start a conversation
        </Link>
      </div>
    </div>
  );
}
