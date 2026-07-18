import { useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  Check,
  Eye,
  EyeOff,
  GitBranch,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";
import { toast } from "sonner";

import logo from "@/assets/clearspecAI-logo.png";
import { useAuth } from "@/context/AuthContext";

import "@/styles/auth-futuristic.css";

const CAPABILITIES = [
  {
    icon: Sparkles,
    title: "Clean",
    description:
      "Transform scattered notes into clear, structured requirements.",
  },
  {
    icon: BarChart3,
    title: "Analyze",
    description:
      "Expose ambiguity, contradictions, gaps, and hidden risks.",
  },
  {
    icon: GitBranch,
    title: "Trace",
    description:
      "Generate database, API, and implementation traceability.",
  },
];

export default function AuthPage({ mode = "login" }) {
  const { login, register } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();
  const pageRef = useRef(null);

  const isLogin = mode === "login";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);

  const handlePointerMove = (event) => {
    if (!pageRef.current) return;

    const bounds = pageRef.current.getBoundingClientRect();

    pageRef.current.style.setProperty(
      "--cs-pointer-x",
      `${event.clientX - bounds.left}px`
    );

    pageRef.current.style.setProperty(
      "--cs-pointer-y",
      `${event.clientY - bounds.top}px`
    );
  };

  const submit = async (event) => {
    event.preventDefault();

    const cleanName = name.trim();
    const cleanEmail = email.trim().toLowerCase();

    if (!isLogin && !cleanName) {
      toast.error("Enter your full name.");
      return;
    }

    if (!cleanEmail) {
      toast.error("Enter your email address.");
      return;
    }

    if (!password) {
      toast.error("Enter your password.");
      return;
    }

    setBusy(true);

    try {
      if (isLogin) {
        await login(cleanEmail, password);
      } else {
        await register(cleanName, cleanEmail, password);
      }

      toast.success(
        isLogin
          ? "Welcome back to ClearSpec AI."
          : "Your ClearSpec AI account is ready."
      );

      const requestedPath = location.state?.from?.pathname;

      navigate(requestedPath || "/app", {
        replace: true,
      });
    } catch (error) {
      console.error("Authentication error:", error);

      toast.error(
        error?.response?.data?.detail ||
          error?.message ||
          "Authentication failed."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <main
      ref={pageRef}
      onPointerMove={handlePointerMove}
      className="cs-auth-page relative min-h-screen overflow-hidden bg-[#020817] text-white"
    >
      {/* Mouse-following glow */}
      <div className="cs-auth-pointer-glow" />

      {/* Full-page animated background */}
      <div className="pointer-events-none absolute inset-0">
        <div className="cs-auth-grid absolute inset-0" />
        <div className="cs-auth-aurora absolute inset-0" />
        <div className="cs-auth-stars absolute inset-0" />
      </div>

      {/* Global charging pulsar reactor */}
      <div
        className="cs-auth-reactor pointer-events-none hidden xl:flex"
        aria-hidden="true"
      >
        <div className="cs-auth-reactor-glow" />

        {/* Expanding energy waves */}
        <div className="cs-auth-shockwave cs-auth-shockwave-a" />
        <div className="cs-auth-shockwave cs-auth-shockwave-b" />
        <div className="cs-auth-shockwave cs-auth-shockwave-c" />

        {/* Horizontal orbit with one dot */}
        <div className="cs-auth-orbit-plane cs-auth-orbit-plane-a">
          <div className="cs-auth-orbit-line" />

          <div className="cs-auth-orbit-runner cs-auth-orbit-runner-a">
            <span className="cs-auth-orbit-dot" />
          </div>
        </div>

        {/* Vertical orbit with one dot */}
        <div className="cs-auth-orbit-plane cs-auth-orbit-plane-b">
          <div className="cs-auth-orbit-line" />

          <div className="cs-auth-orbit-runner cs-auth-orbit-runner-b">
            <span className="cs-auth-orbit-dot" />
          </div>
        </div>

        {/* Diagonal orbit with one dot */}
        <div className="cs-auth-orbit-plane cs-auth-orbit-plane-c">
          <div className="cs-auth-orbit-line" />

          <div className="cs-auth-orbit-runner cs-auth-orbit-runner-c">
            <span className="cs-auth-orbit-dot" />
          </div>
        </div>

        {/* Pulsar beams */}
        <div className="cs-auth-beam cs-auth-beam-vertical" />
        <div className="cs-auth-beam cs-auth-beam-horizontal" />
        <div className="cs-auth-beam cs-auth-beam-diagonal-a" />
        <div className="cs-auth-beam cs-auth-beam-diagonal-b" />

        {/* Rotating 3D cube */}
        <div className="cs-auth-cube-scene">
          <div className="cs-auth-cube">
            <div className="cs-auth-cube-face cs-auth-cube-front" />
            <div className="cs-auth-cube-face cs-auth-cube-back" />
            <div className="cs-auth-cube-face cs-auth-cube-left" />
            <div className="cs-auth-cube-face cs-auth-cube-right" />
            <div className="cs-auth-cube-face cs-auth-cube-top" />
            <div className="cs-auth-cube-face cs-auth-cube-bottom" />
          </div>
        </div>

        {/* Charging core */}
        <div className="cs-auth-energy-core">
          <div className="cs-auth-energy-core-inner" />
        </div>
      </div>

      {/* Main content */}
      <div className="relative z-10 grid min-h-screen xl:grid-cols-[1.05fr_0.95fr]">
        {/* ================= LEFT PANEL ================= */}

        <section className="relative hidden min-h-screen flex-col px-10 py-9 xl:flex 2xl:px-16">
          {/* Large logo above badge */}
          <Link
            to="/"
            aria-label="ClearSpec AI home"
            className="cs-auth-logo-link relative z-20 inline-flex w-fit"
          >
            <img
              src={logo}
              alt="ClearSpec AI"
              className="cs-auth-hero-logo"
            />
          </Link>

          <div className="relative z-10 mt-7 max-w-[680px]">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/[0.07] px-4 py-2 backdrop-blur-xl">
              <Sparkles className="h-3.5 w-3.5 text-cyan-300" />

              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyan-300">
                AI-powered requirements intelligence
              </span>
            </div>

            <h1 className="mt-8 text-[3.8rem] font-semibold leading-[1.03] tracking-[-0.045em] text-white 2xl:text-[4.75rem]">
              From messy notes
              <br />
              to defensible
              <br />

              <span className="bg-gradient-to-r from-cyan-300 via-blue-400 to-violet-400 bg-clip-text text-transparent">
                requirements.
              </span>
            </h1>

            <p className="mt-7 max-w-xl text-base leading-7 text-slate-300">
              ClearSpec AI transforms unstructured stakeholder input into
              standardised user stories, exposes requirement risk, and
              generates implementation-ready technical traceability.
            </p>
          </div>

          {/* Capability cards */}
          <div className="relative z-10 mt-auto grid grid-cols-3 border border-cyan-400/20 bg-slate-950/40 backdrop-blur-xl">
            {CAPABILITIES.map((capability) => {
              const Icon = capability.icon;

              return (
                <article
                  key={capability.title}
                  className="group border-r border-cyan-400/15 p-5 transition hover:bg-cyan-400/[0.04] last:border-r-0"
                >
                  <div className="flex h-10 w-10 items-center justify-center border border-cyan-400/30 bg-cyan-400/[0.06] transition group-hover:border-cyan-300/60 group-hover:shadow-[0_0_24px_rgba(34,211,238,0.18)]">
                    <Icon className="h-4 w-4 text-cyan-300" />
                  </div>

                  <h3 className="mt-4 font-mono text-xs font-semibold uppercase tracking-[0.16em] text-cyan-300">
                    {capability.title}
                  </h3>

                  <p className="mt-2 text-xs leading-5 text-slate-400">
                    {capability.description}
                  </p>
                </article>
              );
            })}
          </div>

          <div className="relative z-10 mt-7 flex items-center gap-2 text-[11px] text-slate-500">
            <ShieldCheck className="h-4 w-4 text-cyan-400" />
            JWT-protected workspace
          </div>
        </section>

        {/* ================= RIGHT AUTH PANEL ================= */}

        <section className="relative flex min-h-screen items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
          <div className="w-full max-w-[560px]">
            {/* Mobile logo */}
            <Link
              to="/"
              aria-label="ClearSpec AI home"
              className="mb-8 inline-flex xl:hidden"
            >
              <img
                src={logo}
                alt="ClearSpec AI"
                className="h-auto w-[260px] max-w-full object-contain sm:w-[330px]"
              />
            </Link>

            <div className="cs-auth-card-shell relative overflow-hidden rounded-[28px] border border-cyan-400/35 bg-[#061326]/90 p-px backdrop-blur-2xl">
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-400/15 via-transparent to-violet-500/15" />

              <form
                onSubmit={submit}
                data-testid="auth-form"
                className="relative rounded-[27px] bg-[#061326]/90 px-6 py-8 sm:px-10 sm:py-10"
              >
                <div className="pointer-events-none absolute -right-20 -top-20 h-60 w-60 rounded-full bg-blue-500/10 blur-3xl" />

                <div className="relative">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_12px_rgba(34,211,238,1)]" />

                    <span className="font-mono text-[10px] uppercase tracking-[0.23em] text-cyan-300">
                      Secure workspace access
                    </span>
                  </div>

                  <h2 className="mt-5 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                    {isLogin ? "Welcome back" : "Create account"}
                  </h2>

                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    {isLogin
                      ? "Sign in to continue to your ClearSpec AI workstation."
                      : "Create your account and begin transforming stakeholder input into defensible requirements."}
                  </p>
                </div>

                {/* Tabs */}
                <div className="relative mt-8 grid grid-cols-2 border-b border-slate-700/80">
                  <Link
                    to="/login"
                    state={location.state}
                    className={`relative py-3 text-center text-sm transition ${
                      isLogin
                        ? "text-white"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    Sign in

                    {isLogin && (
                      <span className="absolute inset-x-0 bottom-[-1px] h-0.5 bg-gradient-to-r from-cyan-300 to-blue-500 shadow-[0_0_10px_rgba(34,211,238,0.8)]" />
                    )}
                  </Link>

                  <Link
                    to="/register"
                    state={location.state}
                    className={`relative py-3 text-center text-sm transition ${
                      !isLogin
                        ? "text-white"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    Create account

                    {!isLogin && (
                      <span className="absolute inset-x-0 bottom-[-1px] h-0.5 bg-gradient-to-r from-blue-400 to-violet-500 shadow-[0_0_10px_rgba(59,130,246,0.8)]" />
                    )}
                  </Link>
                </div>

                {/* Fields */}
                <div className="relative mt-8 space-y-5">
                  {!isLogin && (
                    <div>
                      <label
                        htmlFor="name"
                        className="mb-2 block font-mono text-[10px] uppercase tracking-[0.18em] text-slate-300"
                      >
                        Full name
                      </label>

                      <div className="group relative">
                        <User className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500 transition group-focus-within:text-cyan-300" />

                        <input
                          id="name"
                          name="name"
                          type="text"
                          autoComplete="name"
                          data-testid="auth-name-input"
                          placeholder="Enter your full name"
                          value={name}
                          onChange={(event) => setName(event.target.value)}
                          required
                          disabled={busy}
                          className="h-14 w-full rounded-xl border border-slate-600/80 bg-slate-950/35 pl-12 pr-4 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400/80 focus:shadow-[0_0_22px_rgba(34,211,238,0.12)] disabled:opacity-60"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label
                      htmlFor="email"
                      className="mb-2 block font-mono text-[10px] uppercase tracking-[0.18em] text-slate-300"
                    >
                      Email address
                    </label>

                    <div className="group relative">
                      <Mail className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500 transition group-focus-within:text-cyan-300" />

                      <input
                        id="email"
                        name="email"
                        type="email"
                        autoComplete="email"
                        data-testid="auth-email-input"
                        placeholder="you@company.com"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        required
                        disabled={busy}
                        className="h-14 w-full rounded-xl border border-slate-600/80 bg-slate-950/35 pl-12 pr-4 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400/80 focus:shadow-[0_0_22px_rgba(34,211,238,0.12)] disabled:opacity-60"
                      />
                    </div>
                  </div>

                  <div>
                    <label
                      htmlFor="password"
                      className="mb-2 block font-mono text-[10px] uppercase tracking-[0.18em] text-slate-300"
                    >
                      Password
                    </label>

                    <div className="group relative">
                      <LockKeyhole className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500 transition group-focus-within:text-cyan-300" />

                      <input
                        id="password"
                        name="password"
                        type={showPassword ? "text" : "password"}
                        autoComplete={
                          isLogin ? "current-password" : "new-password"
                        }
                        data-testid="auth-password-input"
                        placeholder={
                          isLogin
                            ? "Enter your password"
                            : "Create at least 6 characters"
                        }
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        required
                        minLength={6}
                        disabled={busy}
                        className="h-14 w-full rounded-xl border border-slate-600/80 bg-slate-950/35 pl-12 pr-14 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400/80 focus:shadow-[0_0_22px_rgba(34,211,238,0.12)] disabled:opacity-60"
                      />

                      <button
                        type="button"
                        onClick={() =>
                          setShowPassword((currentValue) => !currentValue)
                        }
                        disabled={busy}
                        aria-label={
                          showPassword ? "Hide password" : "Show password"
                        }
                        className="absolute right-0 top-0 flex h-14 w-14 items-center justify-center text-slate-500 transition hover:text-cyan-300 disabled:opacity-50"
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {!isLogin && (
                  <div className="relative mt-5 grid gap-2 sm:grid-cols-2">
                    {[
                      "Minimum 6 characters",
                      "Stored as a secure password hash",
                    ].map((requirement) => (
                      <div
                        key={requirement}
                        className="flex items-center gap-2 text-[11px] text-slate-500"
                      >
                        <Check className="h-3 w-3 text-cyan-400" />
                        {requirement}
                      </div>
                    ))}
                  </div>
                )}

                <button
                  type="submit"
                  data-testid="auth-submit-button"
                  disabled={busy}
                  className="relative mt-8 flex h-14 w-full items-center justify-center overflow-hidden rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-violet-600 px-6 text-sm font-semibold text-white shadow-[0_0_30px_rgba(37,99,235,0.38)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {busy ? (
                    <>
                      <span className="mr-3 h-3 w-3 animate-pulse rounded-full bg-white" />

                      {isLogin ? "Signing in..." : "Creating account..."}
                    </>
                  ) : (
                    <>
                      {isLogin ? "Sign in" : "Create account"}

                      <ArrowRight className="ml-3 h-4 w-4" />
                    </>
                  )}
                </button>

                <p className="relative mt-7 text-center text-sm text-slate-500">
                  {isLogin
                    ? "New to ClearSpec AI? "
                    : "Already have an account? "}

                  <Link
                    to={isLogin ? "/register" : "/login"}
                    state={location.state}
                    data-testid="auth-switch-link"
                    className="font-medium text-cyan-300 transition hover:text-cyan-200"
                  >
                    {isLogin ? "Create an account" : "Sign in"}
                  </Link>
                </p>
              </form>
            </div>

            <div className="mt-6 flex items-start justify-center gap-2 text-center text-xs leading-5 text-slate-500">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />

              <span>
                JWT-authenticated access · Requirement history remains linked
                to your account
              </span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}