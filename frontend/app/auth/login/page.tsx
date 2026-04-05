"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Eye, EyeOff, Sparkles } from "lucide-react";
import {
  login_user,
  save_token,
  get_current_user,
  get_profile,
  save_display_name,
  clear_auth,
  get_token,
  type UserOut,
} from "@/lib/api";

/**
 * Renders the login form with email and password fields wired to the backend.
 */
function LoginForm() {
  const router = useRouter();
  const search_params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show_password, setShowPassword] = useState(false);
  const [is_loading, setIsLoading] = useState(false);
  const [error, setError] = useState(
    search_params.get("expired") ? "Your session has expired. Please sign in again." : ""
  );
  const [is_checking_auth, setIsCheckingAuth] = useState(true);

  useEffect(() => {
    /**
     * Redirects already-authenticated users away from the login page so they
     * cannot see it while logged in.
     */
    if (get_token()) {
      router.replace("/");
    } else {
      setIsCheckingAuth(false);
    }
  }, [router]);

  if (is_checking_auth) {
    return null;
  }

  /**
   * Validates fields, authenticates against the backend, saves the JWT and
   * display name, then redirects to the home page.
   */
  async function handle_submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    setIsLoading(true);
    try {
      const { access_token } = await login_user(email, password);
      save_token(access_token);

      let user: UserOut;
      try {
        user = await get_current_user(access_token);
      } catch {
        clear_auth();
        throw new Error("Could not load your account. Please try again.");
      }

      save_display_name(user.display_name ?? user.email);

      const profile = await get_profile(access_token);
      if (!profile.onboarding_completed) {
        router.push("/onboarding");
      } else {
        router.push("/");
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Login failed. Please try again.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5">
            <Image
              src="/logo.png"
              alt="EmoSync"
              width={36}
              height={36}
              className="rounded-sm"
            />
            <span className="text-xl font-semibold tracking-tight">
              EmoSync
            </span>
          </Link>
          <div>
            <h1 className="text-center text-2xl font-bold tracking-tight">
              Welcome back
            </h1>
            <p className="mt-1 text-center text-sm text-muted-foreground">
              Sign in to continue your wellness journey
            </p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <form onSubmit={handle_submit} className="flex flex-col gap-4">
            {/* Email */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="email"
                className="text-sm font-medium text-foreground"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
              />
            </div>

            {/* Password */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-foreground"
                >
                  Password
                </label>
                <Link
                  href="/auth/forgot-password"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={show_password ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-input bg-transparent px-3 py-2 pr-10 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  aria-label={show_password ? "Hide password" : "Show password"}
                >
                  {show_password ? (
                    <EyeOff className="size-4" />
                  ) : (
                    <Eye className="size-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {error}
              </p>
            )}

            {/* Submit */}
            <Button type="submit" className="w-full" disabled={is_loading}>
              {is_loading ? (
                <span className="flex items-center gap-2">
                  <Sparkles className="size-4 animate-spin" />
                  Signing in…
                </span>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>

          {/* Divider */}
          <div className="my-4 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">or</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          {/* Google SSO placeholder */}
          <Button variant="outline" className="w-full" disabled>
            <svg className="mr-2 size-4" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            Continue with Google
          </Button>
        </div>

        {/* Footer link */}
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link
            href="/auth/register"
            className="font-medium text-foreground hover:underline underline-offset-4"
          >
            Get started
          </Link>
        </p>
      </div>
    </div>
  );
}
export default function LoginPage() { return <Suspense fallback={null}><LoginForm /></Suspense>; }
