import { useRef } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Braces,
  Check,
  ChevronRight,
  Database,
  FileSearch,
  FileText,
  GitBranch,
  History,
  LockKeyhole,
  Network,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Upload,
  WandSparkles,
} from "lucide-react";

import logo from "@/assets/clearspecAI-logo.png";
import { useAuth } from "@/context/AuthContext";

import "@/styles/landing-futuristic.css";

const CAPABILITIES = [
  {
    number: "01",
    icon: WandSparkles,
    title: "Standardise",
    description:
      "Convert fragmented stakeholder notes, transcripts, emails, and BRD extracts into structured user stories.",
  },
  {
    number: "02",
    icon: ScanSearch,
    title: "Interrogate",
    description:
      "Surface ambiguity, contradictions, assumptions, missing edge cases, and unresolved questions.",
  },
  {
    number: "03",
    icon: GitBranch,
    title: "Trace",
    description:
      "Translate approved stories into database changes, API contracts, pseudocode, and implementation guidance.",
  },
];

const WORKFLOW = [
  {
    number: "01",
    label: "Input",
    title: "Capture stakeholder evidence",
    description:
      "Paste raw notes or upload PDF, DOCX, TXT, and Markdown documents into a domain-aware workspace.",
    icon: Upload,
  },
  {
    number: "02",
    label: "Clean",
    title: "Generate defensible user stories",
    description:
      "Separate capabilities, identify actors, define business value, and produce measurable acceptance criteria.",
    icon: FileText,
  },
  {
    number: "03",
    label: "Analyze",
    title: "Expose requirement risk",
    description:
      "Audit stories against context to reveal vague language, conflicts, assumptions, and missing failure scenarios.",
    icon: FileSearch,
  },
  {
    number: "04",
    label: "Trace",
    title: "Map implementation impact",
    description:
      "Create linked schema deltas, REST endpoints, core-logic pseudocode, and engineering notes.",
    icon: Network,
  },
];

const SYSTEM_FACTS = [
  {
    value: "03",
    label: "Connected AI stages",
  },
  {
    value: "04",
    label: "Supported file formats",
  },
  {
    value: "01",
    label: "Persistent audit history",
  },
];

const PRINCIPLES = [
  {
    icon: ShieldCheck,
    title: "Human-review first",
    description:
      "Generated requirements remain visible and reviewable. Assumptions and risks are surfaced rather than hidden.",
  },
  {
    icon: LockKeyhole,
    title: "Authenticated workspace",
    description:
      "JWT-based access keeps each user’s analysis records linked to their account.",
  },
  {
    icon: History,
    title: "Persistent history",
    description:
      "Reopen previous analyses, compare outputs, and retain the full Clean → Analyze → Trace chain.",
  },
  {
    icon: Braces,
    title: "Implementation-aware",
    description:
      "Every approved requirement can be connected to data, API, and core application logic.",
  },
];

export default function LandingPage() {
  const { user } = useAuth();
  const pageRef = useRef(null);

  const primaryPath = user ? "/app" : "/register";
  const primaryLabel = user ? "Open workstation" : "Start analysing";

  const handlePointerMove = (event) => {
    if (!pageRef.current) return;

    const bounds = pageRef.current.getBoundingClientRect();

    pageRef.current.style.setProperty(
      "--cs-landing-pointer-x",
      `${event.clientX - bounds.left}px`
    );

    pageRef.current.style.setProperty(
      "--cs-landing-pointer-y",
      `${event.clientY - bounds.top}px`
    );
  };

  return (
    <main
      ref={pageRef}
      onPointerMove={handlePointerMove}
      className="cs-landing-page relative min-h-screen overflow-hidden bg-[#020817] text-white"
    >
      {/* Global background effects */}
      <div className="cs-landing-pointer-glow" />

      <div className="pointer-events-none fixed inset-0">
        <div className="cs-landing-grid absolute inset-0" />
        <div className="cs-landing-aurora absolute inset-0" />
        <div className="cs-landing-stars absolute inset-0" />
      </div>

      {/* ================= NAVIGATION ================= */}

      <header className="cs-landing-nav fixed inset-x-0 top-0 z-50 border-b border-cyan-400/15 bg-[#020817]/75 backdrop-blur-2xl">
        <div className="mx-auto flex h-[74px] max-w-[1500px] items-center justify-between px-5 sm:px-8 lg:px-12">
          <Link
            to="/"
            aria-label="ClearSpec AI home"
            className="cs-landing-logo-link inline-flex items-center"
          >
            <img
              src={logo}
              alt="ClearSpec AI"
              className="h-auto w-[190px] object-contain sm:w-[225px]"
            />
          </Link>

          <nav className="hidden items-center gap-8 lg:flex">
            <a
              href="#capabilities"
              className="cs-landing-nav-link"
            >
              Capabilities
            </a>

            <a
              href="#workflow"
              className="cs-landing-nav-link"
            >
              Workflow
            </a>

            <a
              href="#principles"
              className="cs-landing-nav-link"
            >
              Principles
            </a>
          </nav>

          <div className="flex items-center gap-3">
            {!user && (
              <Link
                to="/login"
                className="hidden px-4 py-2 text-sm text-slate-300 transition hover:text-cyan-300 sm:inline-flex"
              >
                Sign in
              </Link>
            )}

            <Link
              to={primaryPath}
              className="cs-landing-primary-button inline-flex h-11 items-center justify-center rounded-xl px-5 text-sm font-semibold text-white"
            >
              {primaryLabel}

              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* ================= HERO ================= */}

      <section className="relative z-10 min-h-screen pt-[74px]">
        <div className="mx-auto grid min-h-[calc(100vh-74px)] max-w-[1500px] items-center gap-14 px-6 py-20 sm:px-10 lg:grid-cols-[1.02fr_0.98fr] lg:px-12 xl:gap-10">
          {/* Hero copy */}
          <div className="relative z-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/[0.07] px-4 py-2 backdrop-blur-xl">
              <Sparkles className="h-3.5 w-3.5 text-cyan-300" />

              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyan-300">
                AI-powered requirements intelligence
              </span>
            </div>

            <h1 className="mt-8 max-w-[820px] text-[3.6rem] font-semibold leading-[1.01] tracking-[-0.05em] text-white sm:text-[4.8rem] xl:text-[5.65rem]">
              Build clarity
              <br />
              before you
              <br />

              <span className="bg-gradient-to-r from-cyan-300 via-blue-400 to-violet-400 bg-clip-text text-transparent">
                build software.
              </span>
            </h1>

            <p className="mt-7 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
              ClearSpec AI transforms unstructured stakeholder input into
              standardised user stories, identifies hidden requirement risk,
              and produces implementation-ready technical traceability.
            </p>

            <div className="mt-10 flex flex-col gap-3 sm:flex-row">
              <Link
                to={primaryPath}
                className="cs-landing-hero-primary inline-flex h-14 items-center justify-center rounded-xl px-7 text-sm font-semibold text-white"
              >
                {primaryLabel}

                <ArrowRight className="ml-3 h-4 w-4" />
              </Link>

              <a
                href="#workflow"
                className="inline-flex h-14 items-center justify-center rounded-xl border border-slate-600/80 bg-slate-950/30 px-7 text-sm font-medium text-slate-200 backdrop-blur-xl transition hover:border-cyan-400/60 hover:bg-cyan-400/[0.05] hover:text-cyan-200"
              >
                Explore the workflow

                <ChevronRight className="ml-2 h-4 w-4" />
              </a>
            </div>

            <div className="mt-10 flex flex-wrap gap-x-7 gap-y-3">
              {[
                "Domain-aware analysis",
                "Human-review first",
                "Persistent history",
              ].map((item) => (
                <div
                  key={item}
                  className="flex items-center gap-2 text-sm text-slate-400"
                >
                  <span className="flex h-5 w-5 items-center justify-center rounded-full border border-cyan-400/30 bg-cyan-400/[0.07]">
                    <Check className="h-3 w-3 text-cyan-300" />
                  </span>

                  {item}
                </div>
              ))}
            </div>
          </div>

          {/* Futuristic product visualization */}
          <div className="relative mx-auto flex min-h-[590px] w-full max-w-[670px] items-center justify-center">
            <div className="cs-landing-hero-reactor pointer-events-none absolute inset-0">
              <div className="cs-landing-hero-reactor-glow" />

              <div className="cs-landing-hero-ring cs-landing-hero-ring-a" />
              <div className="cs-landing-hero-ring cs-landing-hero-ring-b" />
              <div className="cs-landing-hero-ring cs-landing-hero-ring-c" />

              <div className="cs-landing-hero-cube-scene">
                <div className="cs-landing-hero-cube">
                  <div className="cs-landing-cube-face cs-landing-cube-front" />
                  <div className="cs-landing-cube-face cs-landing-cube-back" />
                  <div className="cs-landing-cube-face cs-landing-cube-left" />
                  <div className="cs-landing-cube-face cs-landing-cube-right" />
                  <div className="cs-landing-cube-face cs-landing-cube-top" />
                  <div className="cs-landing-cube-face cs-landing-cube-bottom" />
                </div>
              </div>

              <div className="cs-landing-hero-core">
                <div className="cs-landing-hero-core-inner" />
              </div>

              <span className="cs-landing-orbit-particle cs-landing-orbit-particle-a" />
              <span className="cs-landing-orbit-particle cs-landing-orbit-particle-b" />
              <span className="cs-landing-orbit-particle cs-landing-orbit-particle-c" />
            </div>

            {/* Product console */}
            <div className="cs-landing-console relative z-10 w-full overflow-hidden rounded-[26px] border border-cyan-400/30 bg-[#061326]/82 backdrop-blur-2xl">
              <div className="flex h-14 items-center justify-between border-b border-cyan-400/15 px-5">
                <div className="flex items-center gap-3">
                  <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_12px_rgba(34,211,238,1)]" />

                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-300">
                    Live requirement analysis
                  </span>
                </div>

                <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-slate-500">
                  Healthcare / 03 stages
                </span>
              </div>

              <div className="grid md:grid-cols-[0.82fr_1.18fr]">
                <div className="border-b border-cyan-400/15 p-5 md:border-b-0 md:border-r">
                  <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-slate-500">
                    Raw stakeholder input
                  </p>

                  <p className="mt-4 text-sm leading-6 text-slate-300">
                    Doctors need faster access to consolidated laboratory
                    results. Critical values must notify the on-call physician
                    within sixty seconds.
                  </p>

                  <div className="mt-6 rounded-xl border border-dashed border-cyan-400/25 bg-cyan-400/[0.04] p-4">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-cyan-300" />

                      <span className="text-xs text-slate-400">
                        Healthcare context applied
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-cyan-300">
                      Structured result
                    </span>

                    <span className="rounded-md border border-blue-400/25 bg-blue-400/[0.08] px-2 py-1 font-mono text-[9px] uppercase text-blue-300">
                      Priority P0
                    </span>
                  </div>

                  <h3 className="mt-4 text-xl font-semibold leading-7 text-white">
                    Notify the on-call physician of critical results
                  </h3>

                  <div className="mt-5 space-y-3 text-sm leading-6 text-slate-400">
                    <p>
                      <strong className="font-medium text-slate-200">
                        As an
                      </strong>{" "}
                      on-call physician
                    </p>

                    <p>
                      <strong className="font-medium text-slate-200">
                        I want
                      </strong>{" "}
                      a critical-result notification within 60 seconds
                    </p>

                    <p>
                      <strong className="font-medium text-slate-200">
                        So that
                      </strong>{" "}
                      urgent patient needs can be addressed promptly
                    </p>
                  </div>

                  <div className="mt-6 rounded-xl border border-amber-400/20 bg-amber-400/[0.05] p-4">
                    <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-amber-300">
                      Conflict detected
                    </p>

                    <p className="mt-2 text-xs leading-5 text-slate-400">
                      The existing 15-minute synchronisation interval conflicts
                      with the required 60-second notification window.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 border-t border-cyan-400/15">
                {[
                  ["01", "Clean"],
                  ["02", "Analyze"],
                  ["03", "Trace"],
                ].map(([number, label]) => (
                  <div
                    key={number}
                    className="border-r border-cyan-400/15 p-4 last:border-r-0"
                  >
                    <p className="font-mono text-[9px] text-slate-600">
                      {number}
                    </p>

                    <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.17em] text-cyan-300">
                      {label}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= SYSTEM FACTS ================= */}

      <section className="relative z-10 border-y border-cyan-400/15 bg-slate-950/35 backdrop-blur-xl">
        <div className="mx-auto grid max-w-[1500px] sm:grid-cols-3">
          {SYSTEM_FACTS.map((fact) => (
            <div
              key={fact.label}
              className="border-b border-cyan-400/15 px-7 py-8 sm:border-b-0 sm:border-r sm:last:border-r-0 lg:px-12"
            >
              <p className="bg-gradient-to-r from-cyan-300 to-violet-400 bg-clip-text text-4xl font-semibold text-transparent">
                {fact.value}
              </p>

              <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
                {fact.label}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ================= CAPABILITIES ================= */}

      <section
        id="capabilities"
        className="relative z-10 px-6 py-28 sm:px-10 lg:px-12"
      >
        <div className="mx-auto max-w-[1400px]">
          <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <div className="inline-flex items-center gap-2">
                <span className="h-px w-10 bg-cyan-300" />

                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyan-300">
                  Core capabilities
                </span>
              </div>

              <h2 className="mt-6 max-w-xl text-4xl font-semibold leading-[1.08] tracking-[-0.035em] text-white sm:text-5xl">
                One controlled pipeline from ambiguity to implementation.
              </h2>
            </div>

            <p className="max-w-2xl self-end text-base leading-7 text-slate-400 lg:justify-self-end">
              ClearSpec AI is designed as an analyst’s workstation rather than a
              generic chatbot. Every stage creates a structured artifact that
              can be reviewed, challenged, and retained.
            </p>
          </div>

          <div className="mt-16 grid gap-5 lg:grid-cols-3">
            {CAPABILITIES.map((capability) => {
              const Icon = capability.icon;

              return (
                <article
                  key={capability.number}
                  className="cs-landing-capability-card group relative overflow-hidden rounded-2xl border border-cyan-400/20 bg-[#061326]/70 p-7 backdrop-blur-xl"
                >
                  <div className="pointer-events-none absolute -right-20 -top-20 h-48 w-48 rounded-full bg-cyan-400/[0.07] blur-3xl transition group-hover:bg-cyan-400/[0.12]" />

                  <div className="relative flex items-center justify-between">
                    <span className="font-mono text-[10px] text-slate-600">
                      {capability.number}
                    </span>

                    <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-400/30 bg-cyan-400/[0.06]">
                      <Icon className="h-5 w-5 text-cyan-300" />
                    </div>
                  </div>

                  <h3 className="relative mt-14 text-2xl font-semibold text-white">
                    {capability.title}
                  </h3>

                  <p className="relative mt-4 text-sm leading-6 text-slate-400">
                    {capability.description}
                  </p>

                  <div className="relative mt-8 h-px w-12 bg-cyan-400/40 transition-all duration-300 group-hover:w-24 group-hover:bg-cyan-300" />
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* ================= WORKFLOW ================= */}

      <section
        id="workflow"
        className="relative z-10 border-y border-cyan-400/15 bg-[#030b1b]/70 px-6 py-28 backdrop-blur-xl sm:px-10 lg:px-12"
      >
        <div className="mx-auto max-w-[1400px]">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2">
              <span className="h-px w-10 bg-blue-400" />

              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-blue-300">
                The ClearSpec workflow
              </span>
            </div>

            <h2 className="mt-6 text-4xl font-semibold leading-[1.08] tracking-[-0.035em] text-white sm:text-5xl">
              Every requirement receives structure, challenge, and a technical
              destination.
            </h2>
          </div>

          <div className="relative mt-16">
            <div className="absolute bottom-0 left-[23px] top-0 hidden w-px bg-gradient-to-b from-cyan-400 via-blue-500 to-violet-500 md:block" />

            <div className="space-y-5">
              {WORKFLOW.map((step) => {
                const Icon = step.icon;

                return (
                  <article
                    key={step.number}
                    className="cs-landing-workflow-row relative grid gap-5 rounded-2xl border border-cyan-400/15 bg-[#061326]/55 p-6 backdrop-blur-xl md:grid-cols-[70px_130px_1fr_48px] md:items-center lg:p-7"
                  >
                    <div className="relative z-10 flex h-12 w-12 items-center justify-center rounded-full border border-cyan-400/40 bg-[#020817] shadow-[0_0_24px_rgba(34,211,238,0.12)]">
                      <span className="font-mono text-[10px] text-cyan-300">
                        {step.number}
                      </span>
                    </div>

                    <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-blue-300">
                      {step.label}
                    </p>

                    <div>
                      <h3 className="text-xl font-semibold text-white">
                        {step.title}
                      </h3>

                      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                        {step.description}
                      </p>
                    </div>

                    <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-blue-400/25 bg-blue-400/[0.06]">
                      <Icon className="h-5 w-5 text-blue-300" />
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ================= PRINCIPLES ================= */}

      <section
        id="principles"
        className="relative z-10 px-6 py-28 sm:px-10 lg:px-12"
      >
        <div className="mx-auto max-w-[1400px]">
          <div className="grid gap-14 lg:grid-cols-[0.82fr_1.18fr]">
            <div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-violet-400/30 bg-violet-400/[0.07]">
                <ShieldCheck className="h-5 w-5 text-violet-300" />
              </div>

              <h2 className="mt-7 max-w-xl text-4xl font-semibold leading-[1.08] tracking-[-0.035em] text-white sm:text-5xl">
                Advanced assistance without surrendering analyst judgment.
              </h2>

              <p className="mt-6 max-w-xl text-base leading-7 text-slate-400">
                ClearSpec AI accelerates requirement engineering while keeping
                assumptions, risks, and generated artifacts visible for human
                review.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {PRINCIPLES.map((principle) => {
                const Icon = principle.icon;

                return (
                  <article
                    key={principle.title}
                    className="cs-landing-principle-card rounded-2xl border border-cyan-400/15 bg-[#061326]/60 p-6 backdrop-blur-xl"
                  >
                    <Icon className="h-5 w-5 text-cyan-300" />

                    <h3 className="mt-5 text-lg font-semibold text-white">
                      {principle.title}
                    </h3>

                    <p className="mt-3 text-sm leading-6 text-slate-400">
                      {principle.description}
                    </p>
                  </article>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ================= FINAL CTA ================= */}

      <section className="relative z-10 border-t border-cyan-400/15 px-6 py-24 sm:px-10 lg:px-12">
        <div className="cs-landing-final-cta mx-auto max-w-[1400px] overflow-hidden rounded-[30px] border border-cyan-400/30 bg-[#061326]/78 p-8 backdrop-blur-2xl sm:p-12 lg:p-16">
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute -right-32 -top-32 h-80 w-80 rounded-full bg-cyan-400/10 blur-3xl" />
            <div className="absolute -bottom-36 left-[35%] h-80 w-80 rounded-full bg-violet-500/10 blur-3xl" />
          </div>

          <div className="relative flex flex-col justify-between gap-10 lg:flex-row lg:items-end">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyan-300">
                Build clarity before code
              </p>

              <h2 className="mt-5 max-w-4xl text-4xl font-semibold leading-[1.06] tracking-[-0.035em] text-white sm:text-5xl lg:text-6xl">
                Turn uncertain stakeholder input into requirements your team can
                defend and implement.
              </h2>
            </div>

            <Link
              to={primaryPath}
              className="cs-landing-hero-primary inline-flex h-14 shrink-0 items-center justify-center rounded-xl px-7 text-sm font-semibold text-white"
            >
              {primaryLabel}

              <ArrowRight className="ml-3 h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ================= FOOTER ================= */}

      <footer className="relative z-10 border-t border-cyan-400/15 bg-[#020817]/80 px-6 py-8 backdrop-blur-xl sm:px-10 lg:px-12">
        <div className="mx-auto flex max-w-[1400px] flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <img
            src={logo}
            alt="ClearSpec AI"
            className="h-auto w-[190px] object-contain"
          />

          <p className="text-xs text-slate-500">
            Requirements intelligence for modern Business Analysts.
          </p>
        </div>
      </footer>
    </main>
  );
}