"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import {
  GoogleLogin,
  type CredentialResponse,
} from "@react-oauth/google";
import {
  ArrowLeft,
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Orbit,
  UserRound,
} from "lucide-react";
import SignalField from "./SignalField";

type AuthPageProps = {
  mode: "login" | "signup";
};

type AuthResponse = {
  success?: boolean;
  message?: string;
  error?: string;
  token?: string;
  accessToken?: string;
  user?: {
    id?: number | string;
    email?: string;
    token?: string;
  };
};

export default function AuthPage({ mode }: AuthPageProps) {
  const isSignup = mode === "signup";
  const router = useRouter();
  const reduceMotion = useReducedMotion() ?? false;

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState<"error" | "success">(
    "error"
  );
  const [googleButtonWidth, setGoogleButtonWidth] = useState(280);

  useEffect(() => {
    const updateWidth = () => {
      setGoogleButtonWidth(
        Math.min(400, Math.max(200, window.innerWidth - 120))
      );
    };

    updateWidth();
    window.addEventListener("resize", updateWidth);

    return () => {
      window.removeEventListener("resize", updateWidth);
    };
  }, []);

  const inputClass = `w-full min-w-0 bg-transparent ${
    isSignup ? "py-2.5" : "py-3"
  } pl-3 pr-3 text-sm text-white outline-none placeholder:text-white/30`;

  const labelClass = `${
    isSignup ? "mb-1.5" : "mb-2"
  } block text-xs font-medium text-white/80`;

  const inputWrapperClass =
    "flex items-center rounded-xl border border-white/10 bg-[#0B121C]/70 transition duration-300 hover:border-white/20 focus-within:border-cyan-300/60 focus-within:shadow-[0_0_0_3px_rgba(34,211,238,0.06)]";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("");

    const form = new FormData(event.currentTarget);

    const email = form.get("email")?.toString().trim() ?? "";
    const password = form.get("password")?.toString() ?? "";
    const name = form.get("name")?.toString().trim() ?? "";
    const confirmPassword =
      form.get("confirmPassword")?.toString() ?? "";

    if (isSignup && password.length < 8) {
      setStatusType("error");
      setStatus("Password must be at least 8 characters.");
      return;
    }

    if (isSignup && password !== confirmPassword) {
      setStatusType("error");
      setStatus("Your passwords do not match. Please try again.");
      return;
    }

    setLoading(true);

    try {
      const baseURL = (
        process.env.NEXT_PUBLIC_API_URL ||
        "http://localhost:3000/api"
      ).replace(/\/+$/, "");

      const response = await fetch(
        `${baseURL}/auth/${isSignup ? "signup" : "login"}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(
            isSignup
              ? { name, email, password }
              : { email, password }
          ),
        }
      );

      const result = (await response.json().catch(() => ({}))) as AuthResponse;

      if (!response.ok) {
        setStatusType("error");
        setStatus(
          result.message ||
            result.error ||
            (isSignup
              ? "Unable to create your account."
              : "Invalid email or password.")
        );
        return;
      }

      // Your backend may return the token at the top level or inside user.
      const token =
        result.token ||
        result.accessToken ||
        result.user?.token;

      if (token) {
        sessionStorage.setItem("scout_token", token);
        router.push("/research");
        return;
      }

      if (isSignup) {
        setStatusType("success");
        setStatus(
          "Account created successfully. Please sign in to continue."
        );

        window.setTimeout(() => {
          router.push("/login");
        }, 1200);

        return;
      }

      setStatusType("error");
      setStatus(
        "The server did not return a login token. Please check your backend response."
      );
    } catch {
      setStatusType("error");
      setStatus(
        "Could not connect to Scout's backend. Check that the Node.js server is running."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleSuccess(
    googleResponse: CredentialResponse
  ) {
    const credential = googleResponse.credential;

    if (!credential) {
      setStatusType("error");
      setStatus("Google sign-in failed. Please try again.");
      return;
    }

    setLoading(true);
    setStatus("");

    try {
      const baseURL = (
        process.env.NEXT_PUBLIC_API_URL ||
        "http://localhost:3000/api"
      ).replace(/\/+$/, "");

      const response = await fetch(`${baseURL}/auth/google`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ credential }),
      });

      const result = (await response
        .json()
        .catch(() => ({}))) as AuthResponse;

      if (!response.ok) {
        setStatusType("error");
        setStatus(
          result.error || "Google sign-in failed. Please try again."
        );
        return;
      }

      const token =
        result.token ||
        result.accessToken ||
        result.user?.token;

      if (!token) {
        setStatusType("error");
        setStatus("Authentication token was not returned.");
        return;
      }

      sessionStorage.setItem("scout_token", token);
      router.push("/research");
    } catch (error) {
      console.error("Google sign-in failed:", error);
      setStatusType("error");
      setStatus("Could not connect to Scout's backend.");
    } finally {
      setLoading(false);
    }
  }

  function handleForgotPassword() {
    setStatusType("error");
    setStatus("Password recovery has not been implemented yet.");
  }

  return (
    <>
      <SignalField />

      <main className="relative z-10 flex min-h-screen flex-col text-[#F4F7FB]">
        {/* Header */}
        <header className="absolute inset-x-0 top-0 z-20 flex w-full items-center justify-between px-6 py-5 md:px-10">
          <Link href="/" className="flex items-center gap-2.5">
            <Orbit
              className="h-7 w-7 text-cyan-300"
              strokeWidth={1.6}
            />

            <span className="font-[family-name:var(--font-scout-wordmark)] text-2xl font-bold tracking-[-0.075em]">
              S C O U T<span className="text-cyan-300"></span>
            </span>
          </Link>

          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-white/60 transition hover:text-white"
          >
            <ArrowLeft size={15} />
            Back to home
          </Link>
        </header>

        {/* Main layout */}
        <div className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-12 px-6 pb-6 pt-16 lg:grid-cols-[1fr_0.85fr] lg:gap-20 lg:px-10">
          {/* Left editorial section */}
          <motion.section
            initial={reduceMotion ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="hidden lg:block"
          >
            <p className="mb-6 text-xs tracking-[0.25em] text-cyan-300/80">
              YOUR RESEARCH, CONTINUED
            </p>

            <h1 className="max-w-xl text-5xl font-medium leading-[1.12] tracking-[-0.055em] xl:text-7xl">
              {isSignup ? (
                <>
                  Make room for
                  <br />
                  <span className="font-serif font-normal italic text-cyan-300">
                    new discoveries.
                  </span>
                </>
              ) : (
                <>
                  Your next
                  <br />
                  <span className="font-serif font-normal italic text-cyan-300">
                    discovery awaits.
                  </span>
                </>
              )}
            </h1>

            <p className="mt-7 max-w-md text-base leading-7 text-white/60">
              {isSignup
                ? "Create your Scout account and turn your curiosity into structured, source-backed research."
                : "Pick up your research and keep exploring the questions that matter to you."}
            </p>

            <div className="mt-12 max-w-md border-t border-white/15 pt-5">
              <div className="flex items-center justify-between text-[10px] tracking-[0.16em] text-white/45">
                <span>DISCOVER</span>
                <span className="text-cyan-300">CONNECT</span>
                <span>UNDERSTAND</span>
              </div>

              <div className="mt-4 flex gap-1.5">
                <div className="h-px flex-1 bg-cyan-300" />
                <div className="h-px flex-1 bg-cyan-300/50" />
                <div className="h-px flex-1 bg-white/15" />
              </div>
            </div>
          </motion.section>

          {/* Authentication panel */}
          <motion.section
            initial={reduceMotion ? false : { opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="mx-auto w-full max-w-md"
          >
            {/* Transparent card */}
            <div className={`relative overflow-hidden rounded-2xl border border-white/[0.12] bg-transparent p-6 ${
                isSignup ? "sm:p-6" : "sm:p-8"
              }`}>
              <div
                aria-hidden="true"
                className="pointer-events-none absolute left-8 right-8 top-0 h-px bg-gradient-to-r from-transparent via-cyan-300/70 to-transparent"
              />

              {/* Form heading */}
              <div className={isSignup ? "mb-4" : "mb-6"}>
                <div className="flex items-center gap-4">
                  {/* Logo icon */}
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-cyan-300/25 bg-cyan-300/[0.07]">
                    <Orbit className="h-6 w-6 text-cyan-300" />
                  </div>

                  {/* Heading beside logo */}
                  <div className="min-w-0">
                    <h2 className="text-2xl font-medium leading-tight tracking-[-0.045em] sm:text-3xl">
                      {isSignup ? (
                        <>
                          Create your{" "}
                          <span className="font-serif font-normal italic text-cyan-300">
                            account.
                          </span>
                        </>
                      ) : (
                        <>
                          Welcome{" "}
                          <span className="font-serif font-normal italic text-cyan-300">
                            back.
                          </span>
                        </>
                      )}
                    </h2>
                  </div>
                </div>

                {/* Description below */}
                <p className="mt-3 text-sm leading-6 text-white/65">
                  {isSignup
                    ? "One account. More room to explore."
                    : "Sign in to continue your research and pick up where you left off."}
                </p>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className={isSignup ? "space-y-3" : "space-y-4"}>
                {isSignup && (
                  <div>
                    <label
                      htmlFor="name"
                      className={labelClass}
                    >
                      Your name
                    </label>

                    <div className={inputWrapperClass}>
                      <UserRound
                        size={17}
                        className="ml-4 shrink-0 text-white/45"
                      />

                      <input
                        id="name"
                        name="name"
                        type="text"
                        autoComplete="name"
                        placeholder="Enter your name"
                        maxLength={100}
                        required
                        className={inputClass}
                      />
                    </div>
                  </div>
                )}

                {/* Email */}
                <div>
                  <label
                    htmlFor="email"
                    className={labelClass}
                  >
                    Email address
                  </label>

                  <div className={inputWrapperClass}>
                    <Mail
                      size={17}
                      className="ml-4 shrink-0 text-white/45"
                    />

                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      maxLength={254}
                      required
                      className={inputClass}
                    />
                  </div>
                </div>

                {/* Password */}
                <div>
                  <div className={`${isSignup ? "mb-1.5" : "mb-2"} flex items-center justify-between gap-3`}>
                    <label
                      htmlFor="password"
                      className="text-xs font-medium text-white/80"
                    >
                      Password
                    </label>
                  </div>

                  <div className={inputWrapperClass}>
                    <LockKeyhole
                      size={17}
                      className="ml-4 shrink-0 text-white/45"
                    />

                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete={
                        isSignup ? "new-password" : "current-password"
                      }
                      placeholder={
                        isSignup
                          ? "At least 8 characters"
                          : "Enter your password"
                      }
                      minLength={isSignup ? 8 : undefined}
                      required
                      className={inputClass}
                    />

                    <button
                      type="button"
                      aria-label={
                        showPassword ? "Hide password" : "Show password"
                      }
                      onClick={() => setShowPassword(!showPassword)}
                      className="mr-4 shrink-0 text-white/45 transition hover:text-cyan-300"
                    >
                      {showPassword ? (
                        <EyeOff size={17} />
                      ) : (
                        <Eye size={17} />
                      )}
                    </button>
                  </div>
                </div>

                {/* Confirm password */}
                {isSignup && (
                  <div>
                    <label
                      htmlFor="confirmPassword"
                      className={labelClass}
                    >
                      Confirm password
                    </label>

                    <div className={inputWrapperClass}>
                      <LockKeyhole
                        size={17}
                        className="ml-4 shrink-0 text-white/45"
                      />

                      <input
                        id="confirmPassword"
                        name="confirmPassword"
                        type={showConfirmPassword ? "text" : "password"}
                        autoComplete="new-password"
                        placeholder="Enter your password again"
                        minLength={8}
                        required
                        className={inputClass}
                      />

                      <button
                        type="button"
                        aria-label={
                          showConfirmPassword
                            ? "Hide confirmation password"
                            : "Show confirmation password"
                        }
                        onClick={() =>
                          setShowConfirmPassword(!showConfirmPassword)
                        }
                        className="mr-4 shrink-0 text-white/45 transition hover:text-cyan-300"
                      >
                        {showConfirmPassword ? (
                          <EyeOff size={17} />
                        ) : (
                          <Eye size={17} />
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {/* Status message */}
                {status && (
                  <p
                    role="status"
                    aria-live="polite"
                    className={`rounded-lg border px-3 py-2.5 text-xs leading-5 ${
                      statusType === "success"
                        ? "border-cyan-300/20 bg-cyan-300/[0.06] text-cyan-200"
                        : "border-red-300/20 bg-red-400/[0.06] text-red-200"
                    }`}
                  >
                    {status}
                  </p>
                )}

                {/* Submit */}
                <button
                  type="submit"
                  disabled={loading}
                  className="group flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-300 px-5 py-3.5 text-sm font-semibold text-[#061019] shadow-[0_0_24px_rgba(34,211,238,0.12)] transition duration-300 hover:-translate-y-0.5 hover:bg-cyan-200 hover:shadow-[0_0_32px_rgba(34,211,238,0.22)] active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading
                    ? "Please wait..."
                    : isSignup
                      ? "Create account"
                      : "Sign in"}

                  {!loading && (
                    <ArrowRight
                      size={16}
                      className="transition-transform group-hover:translate-x-1"
                    />
                  )}
                </button>
              </form>

              {/* Google sign-in option */}
              <div className="mt-5 w-full">
                <div className="mb-4 flex items-center gap-3">
                  <div className="h-px flex-1 bg-white/10" />

                  <span className="text-[10px] font-medium tracking-[0.16em] text-white/45">
                    OR CONTINUE WITH
                  </span>

                  <div className="h-px flex-1 bg-white/10" />
                </div>

                <div className="flex w-full justify-center">
                  <GoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={() => {
                      setStatusType("error");
                      setStatus("Google sign-in failed. Please try again.");
                    }}
                    text="continue_with"
                    shape="rectangular"
                    theme="filled_black"
                    size="large"
                    width={String(googleButtonWidth)}
                  />
                </div>

                {!isSignup && (
                  <p className="mt-3 text-center text-[11px] text-white/40">
                    Quick, secure access to your Scout account.
                  </p>
                )}
              </div>

              {/* Login/signup switch */}
              <div className={`${isSignup ? "my-4" : "my-5"} flex items-center gap-3`}>
                <div className="h-px flex-1 bg-white/10" />

                <span className="text-[10px] tracking-[0.12em] text-white/45">
                  {isSignup ? "ALREADY WITH SCOUT?" : "NEW TO SCOUT?"}
                </span>

                <div className="h-px flex-1 bg-white/10" />
              </div>

              <p className="text-center text-sm text-white/70">
                {isSignup
                  ? "Already have an account?"
                  : "Ready to explore?"}{" "}

                <Link
                  href={isSignup ? "/login" : "/signup"}
                  className="font-medium text-cyan-300 transition hover:text-cyan-200"
                >
                  {isSignup ? "Sign in" : "Create account"}
                </Link>
              </p>
            </div>

            <p className={`mt-4 text-center text-[10px] tracking-[0.08em] text-white/45 ${
                isSignup ? "hidden" : ""
              }`}>
              BUILT FOR THE CURIOUS. DESIGNED FOR DEEPER RESEARCH.
            </p>
          </motion.section>
        </div>
      </main>
    </>
  );
}