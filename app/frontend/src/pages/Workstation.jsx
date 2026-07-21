import logo from "@/assets/clearspecAI-logo.png";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Clock3,
  FileText,
  FileUp,
  History,
  LoaderCircle,
  LogOut,
  PanelLeft,
  Plus,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { csApi } from "@/lib/api";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { Markdown } from "@/components/ui/Markdown";

import "@/styles/workstation-futuristic.css";

const DOMAINS = [
  { value: "general", label: "General" },
  { value: "healthcare", label: "Healthcare" },
  { value: "finance", label: "Finance" },
  { value: "retail", label: "Retail" },
  { value: "logistics", label: "Logistics" },
  { value: "saas", label: "SaaS" },
];

const HINTS = {
  stories: {
    n: "02",
    eyebrow: "NORMALISE",
    t: "Standardised User Stories",
    d: "Transform raw stakeholder material into INVEST-oriented user stories with explicit assumptions, measurable acceptance criteria, priorities and estimates.",
  },
  gap: {
    n: "03",
    eyebrow: "AUDIT",
    t: "Gap & Conflict Analysis",
    d: "Expose ambiguity, missing requirements, contradictions, delivery risks and stakeholder decisions before implementation begins.",
  },
  trace: {
    n: "04",
    eyebrow: "ARCHITECT",
    t: "Technical Traceability",
    d: "Generate traceable database, API, workflow, security and test artifacts—with deterministic validation and visible review warnings.",
  },
};

const STAGES = [
  { key: "stories", number: "02", label: "Stories" },
  { key: "gap", number: "03", label: "Gap Analysis" },
  { key: "trace", number: "04", label: "Technical Trace" },
];

function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (detail && typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return "Pipeline failed.";
    }
  }

  return error?.message || "Pipeline failed.";
}

export default function Workstation() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const [rawText, setRawText] = useState("");
  const [domain, setDomain] = useState("general");
  const [context, setContext] = useState("");

  const [historyId, setHistoryId] = useState(null);
  const [storiesMd, setStoriesMd] = useState("");
  const [gapMd, setGapMd] = useState("");
  const [traceMd, setTraceMd] = useState("");

  const [busyClean, setBusyClean] = useState(false);
  const [busyAnalyze, setBusyAnalyze] = useState(false);
  const [busyTrace, setBusyTrace] = useState(false);
  const [busyUpload, setBusyUpload] = useState(false);

  const [tab, setTab] = useState("stories");
  const [history, setHistory] = useState([]);
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false);

  const fileRef = useRef(null);
  const historyRequestedRef = useRef(false);

  const isBusy = busyClean || busyAnalyze || busyTrace;
  const traceNeedsReview = useMemo(
    () => /Validation Review Required/i.test(traceMd),
    [traceMd]
  );

  const loadHistory = useCallback(async () => {
    try {
      const items = await csApi.history();
      setHistory(Array.isArray(items) ? items : []);
    } catch (error) {
      console.error("Could not load history:", error);
    }
  }, []);

  useEffect(() => {
    // React StrictMode runs effects twice in development. This guard prevents
    // duplicate history requests without disabling StrictMode.
    if (historyRequestedRef.current) return;

    historyRequestedRef.current = true;
    void loadHistory();
  }, [loadHistory]);

  const resetWorkspace = () => {
    setHistoryId(null);
    setRawText("");
    setDomain("general");
    setContext("");
    setStoriesMd("");
    setGapMd("");
    setTraceMd("");
    setTab("stories");
    setMobileHistoryOpen(false);

    if (fileRef.current) {
      fileRef.current.value = "";
    }
  };

  const onClean = async () => {
    if (rawText.trim().length < 10) {
      toast.error("Add at least 10 characters of stakeholder input.");
      return;
    }

    setStoriesMd("");
    setGapMd("");
    setTraceMd("");
    setTab("stories");
    setBusyClean(true);

    let createdHistoryId = null;
    let activeStage = "stories";

    try {
      const cleanResult = await csApi.clean({
        raw_text: rawText,
        domain,
      });

      createdHistoryId = cleanResult.id;
      setHistoryId(cleanResult.id);
      setStoriesMd(cleanResult.stories_md);
      setBusyClean(false);

      // One refresh is enough to expose the newly created record in History.
      await loadHistory();

      activeStage = "gap";
      setTab("gap");
      setBusyAnalyze(true);

      const analyzeResult = await csApi.analyze({
        stories: cleanResult.stories_md,
        context,
        history_id: cleanResult.id,
      });

      setGapMd(analyzeResult.gap_md);
      setBusyAnalyze(false);

      activeStage = "trace";
      setTab("trace");
      setBusyTrace(true);

      const traceResult = await csApi.trace({
        stories: cleanResult.stories_md,
        history_id: cleanResult.id,
      });

      setTraceMd(traceResult.trace_md);
      setBusyTrace(false);
      setTab("trace");

      toast.success(
        /Validation Review Required/i.test(traceResult.trace_md)
          ? "Pipeline complete with review items."
          : "Pipeline complete."
      );
    } catch (error) {
      console.error(error);

      setTab(activeStage);
      toast.error(getErrorMessage(error));

      // A clean-stage record may already exist even if a later stage failed.
      if (createdHistoryId) {
        await loadHistory();
      }
    } finally {
      setBusyClean(false);
      setBusyAnalyze(false);
      setBusyTrace(false);
    }
  };

  const onUpload = async (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setBusyUpload(true);

    try {
      const { text, filename } = await csApi.extract(file);

      setRawText((previous) =>
        previous
          ? `${previous}\n\n--- ${filename} ---\n${text}`
          : text
      );

      toast.success(`Extracted ${filename}`);
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          "Could not parse the selected file."
      );
    } finally {
      setBusyUpload(false);
      event.target.value = "";
    }
  };

  const openHistory = async (id) => {
    try {
      const doc = await csApi.getHistory(id);

      setHistoryId(doc.id);
      setRawText(doc.raw_text || "");
      setDomain(doc.domain || "general");
      setContext(doc.context || "");
      setStoriesMd(doc.stories_md || "");
      setGapMd(doc.gap_md || "");
      setTraceMd(doc.trace_md || "");

      if (doc.trace_md) {
        setTab("trace");
      } else if (doc.gap_md) {
        setTab("gap");
      } else {
        setTab("stories");
      }

      setMobileHistoryOpen(false);
    } catch (error) {
      console.error(error);
      toast.error("Could not load this record.");
    }
  };

  const removeHistory = async (id, event) => {
    event.preventDefault();
    event.stopPropagation();

    try {
      await csApi.deleteHistory(id);

      if (id === historyId) {
        resetWorkspace();
      }

      setHistory((items) =>
        items.filter((item) => item.id !== id)
      );

      toast.success("History record deleted.");
    } catch (error) {
      console.error(error);
      toast.error("Delete failed.");
    }
  };

  const fmtDate = (iso) => {
    try {
      return new Date(iso).toLocaleString(undefined, {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const stageState = (stageKey) => {
    if (stageKey === "stories") {
      if (busyClean) return "running";
      if (storiesMd) return "complete";
      return "idle";
    }

    if (stageKey === "gap") {
      if (busyAnalyze) return "running";
      if (gapMd) return "complete";
      return "idle";
    }

    if (busyTrace) return "running";
    if (traceMd && traceNeedsReview) return "review";
    if (traceMd) return "complete";
    return "idle";
  };

  const currentStageLabel = busyClean
    ? "NORMALISING INPUT"
    : busyAnalyze
      ? "AUDITING REQUIREMENTS"
      : busyTrace
        ? "GENERATING TRACE"
        : traceNeedsReview
          ? "COMPLETE · REVIEW REQUIRED"
          : traceMd
            ? "PIPELINE COMPLETE"
            : "SYSTEM READY";

  return (
    <div className="cs-workstation">
      <div className="cs-workstation__grid" aria-hidden="true" />
      <div className="cs-workstation__glow" aria-hidden="true" />

      <header className="cs-topbar">
        <div className="cs-brand">
          <button
            type="button"
            className="cs-mobile-history-button"
            aria-label="Open history"
            onClick={() => setMobileHistoryOpen(true)}
          >
            <PanelLeft size={18} />
          </button>

          <div className="cs-brand__logo-wrap">
            <img
              src={logo}
              alt="ClearSpec AI"
              className="cs-brand__logo-image"
            />
          </div>

          <div className="cs-brand__copy">
            <span className="cs-brand__divider" aria-hidden="true" />
            <span className="cs-brand__descriptor">
              REQUIREMENT ENGINEERING WORKSTATION
            </span>
          </div>
        </div>

        <div className="cs-topbar__actions">
          <div
            className={`cs-system-state ${
              isBusy ? "is-running" : ""
            } ${traceNeedsReview ? "is-review" : ""}`}
          >
            <span className="cs-system-state__pulse" />
            <Activity size={14} />
            <span>{currentStageLabel}</span>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                data-testid="user-menu-button"
                className="cs-user-button"
                aria-label="Open user menu"
              >
                <span className="cs-user-button__avatar">
                  {user?.name?.[0]?.toUpperCase() || "U"}
                </span>

                <span className="cs-user-button__identity">
                  <span className="cs-user-button__email">
                    {user?.email}
                  </span>
                  <span className="cs-user-button__role">
                    AUTHENTICATED OPERATOR
                  </span>
                </span>

                <ChevronDown size={15} />
              </button>
            </DropdownMenuTrigger>

            <DropdownMenuContent
              align="end"
              className="cs-user-menu"
            >
              <DropdownMenuLabel className="cs-user-menu__label">
                SIGNED IN
              </DropdownMenuLabel>

              <DropdownMenuItem
                disabled
                className="cs-user-menu__item"
              >
                {user?.name || user?.email}
              </DropdownMenuItem>

              <DropdownMenuSeparator className="cs-user-menu__separator" />

              <DropdownMenuItem
                data-testid="logout-menu-item"
                className="cs-user-menu__item cs-user-menu__logout"
                onClick={() => {
                  logout();
                  nav("/login", { replace: true });
                }}
              >
                <LogOut size={16} />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <div className="cs-workstation__body">
        <HistoryPanel
          history={history}
          historyId={historyId}
          fmtDate={fmtDate}
          onOpen={openHistory}
          onRemove={removeHistory}
          onReset={resetWorkspace}
          className="cs-history-panel--desktop"
        />

        {mobileHistoryOpen && (
          <div
            className="cs-mobile-history-overlay"
            role="presentation"
            onMouseDown={(event) => {
              if (event.target === event.currentTarget) {
                setMobileHistoryOpen(false);
              }
            }}
          >
            <div className="cs-mobile-history-sheet">
              <div className="cs-mobile-history-sheet__top">
                <span>WORKSPACE HISTORY</span>
                <button
                  type="button"
                  aria-label="Close history"
                  onClick={() => setMobileHistoryOpen(false)}
                >
                  <X size={18} />
                </button>
              </div>

              <HistoryPanel
                history={history}
                historyId={historyId}
                fmtDate={fmtDate}
                onOpen={openHistory}
                onRemove={removeHistory}
                onReset={resetWorkspace}
                className="cs-history-panel--mobile"
              />
            </div>
          </div>
        )}

        <section className="cs-input-panel">
          <div className="cs-panel-heading">
            <div>
              <span className="cs-panel-heading__number">01</span>
              <span className="cs-panel-heading__slash">/</span>
              <span className="cs-panel-heading__title">
                SOURCE INPUT
              </span>
            </div>

            <div className="cs-panel-heading__meta">
              <FileText size={13} />
              <span>{rawText.length.toLocaleString()} CHARS</span>
            </div>
          </div>

          <div className="cs-input-panel__scroll">
            <div className="cs-control-grid">
              <div className="cs-field">
                <Label className="cs-field__label">
                  DOMAIN PROFILE
                </Label>

                <Select
                  value={domain}
                  onValueChange={setDomain}
                  disabled={isBusy}
                >
                  <SelectTrigger
                    data-testid="domain-select-trigger"
                    className="cs-select-trigger"
                  >
                    <SelectValue />
                  </SelectTrigger>

                  <SelectContent className="cs-select-content">
                    {DOMAINS.map((item) => (
                      <SelectItem
                        key={item.value}
                        value={item.value}
                        data-testid={`domain-option-${item.value}`}
                        className="cs-select-item"
                      >
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="cs-field">
                <Label className="cs-field__label">
                  SOURCE DOCUMENT
                </Label>

                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  className="hidden"
                  onChange={onUpload}
                  data-testid="file-input"
                />

                <Button
                  type="button"
                  variant="outline"
                  data-testid="upload-button"
                  disabled={busyUpload || isBusy}
                  onClick={() => fileRef.current?.click()}
                  className="cs-upload-button"
                >
                  {busyUpload ? (
                    <LoaderCircle
                      className="cs-spin"
                      size={16}
                    />
                  ) : (
                    <FileUp size={16} />
                  )}
                  {busyUpload ? "Extracting..." : "Upload PDF / DOCX / TXT"}
                </Button>
              </div>
            </div>

            <div className="cs-field cs-field--grow">
              <div className="cs-field__heading-row">
                <Label className="cs-field__label">
                  RAW STAKEHOLDER NOTES
                </Label>

                <span className="cs-field__hint">
                  MINIMUM 10 CHARACTERS
                </span>
              </div>

              <Textarea
                data-testid="raw-text-input"
                value={rawText}
                disabled={isBusy}
                onChange={(event) =>
                  setRawText(event.target.value)
                }
                placeholder={`Paste meeting notes, emails, BRD excerpts or transcript text...

Example:
"Doctors need faster access to consolidated laboratory results.
Critical values must notify the on-call physician within sixty seconds."`}
                className="cs-textarea cs-textarea--primary"
              />
            </div>

            <div className="cs-field">
              <div className="cs-field__heading-row">
                <Label className="cs-field__label">
                  EXISTING SYSTEM CONTEXT
                </Label>

                <span className="cs-field__optional">OPTIONAL</span>
              </div>

              <Textarea
                data-testid="context-input"
                value={context}
                disabled={isBusy}
                onChange={(event) =>
                  setContext(event.target.value)
                }
                placeholder="Backlog fragments, current workflows, integrations, architecture constraints..."
                className="cs-textarea cs-textarea--context"
              />
            </div>
          </div>

          <div className="cs-pipeline-console">
            <div className="cs-pipeline-console__stages">
              {STAGES.map((stage) => {
                const state = stageState(stage.key);

                return (
                  <div
                    key={stage.key}
                    className={`cs-mini-stage is-${state}`}
                  >
                    <span className="cs-mini-stage__dot">
                      {state === "running" ? (
                        <LoaderCircle
                          className="cs-spin"
                          size={12}
                        />
                      ) : state === "complete" ? (
                        <CheckCircle2 size={12} />
                      ) : state === "review" ? (
                        <AlertTriangle size={12} />
                      ) : (
                        <Clock3 size={12} />
                      )}
                    </span>
                    <span>{stage.number}</span>
                  </div>
                );
              })}
            </div>

            <Button
              type="button"
              data-testid="run-pipeline-button"
              onClick={onClean}
              disabled={isBusy || busyUpload}
              className="cs-run-button"
            >
              {isBusy ? (
                <LoaderCircle
                  className="cs-spin"
                  size={18}
                />
              ) : (
                <Sparkles size={18} />
              )}

              <span>
                {busyClean
                  ? "STANDARDISING REQUIREMENTS"
                  : busyAnalyze
                    ? "AUDITING GAPS & CONFLICTS"
                    : busyTrace
                      ? "GENERATING TECHNICAL TRACE"
                      : "RUN CLEARSPEC AI PIPELINE"}
              </span>
            </Button>

            <div className="cs-pipeline-console__foot">
              <ShieldCheck size={13} />
              <span>
                THREE-STAGE VALIDATION · AUTOMATIC REPAIR ·
                REVIEW WARNINGS
              </span>
            </div>
          </div>
        </section>

        <section className="cs-results-panel">
          <Tabs
            value={tab}
            onValueChange={setTab}
            className="cs-results-tabs"
          >
            <div className="cs-results-tabs__top">
              <TabsList className="cs-tabs-list">
                {STAGES.map((stage) => {
                  const state = stageState(stage.key);

                  return (
                    <TabsTrigger
                      key={stage.key}
                      value={stage.key}
                      data-testid={`tab-${stage.key}`}
                      className="cs-tab-trigger"
                    >
                      <span className="cs-tab-trigger__number">
                        {stage.number}
                      </span>
                      <span className="cs-tab-trigger__label">
                        {stage.label}
                      </span>
                      <span
                        className={`cs-tab-trigger__state is-${state}`}
                        aria-label={`${stage.label}: ${state}`}
                      />
                    </TabsTrigger>
                  );
                })}
              </TabsList>

              <div className="cs-results-tabs__engine">
                <span className="cs-results-tabs__engine-dot" />
                OPENROUTER / VALIDATED
              </div>
            </div>

            <div className="cs-result-viewport">
              <TabsContent
                value="stories"
                className="cs-tab-content"
                data-testid="panel-stories"
              >
                {busyClean && (
                  <PipelineLoader
                    label="Standardising user stories"
                    stage="02"
                    testId="loader-stories"
                  />
                )}

                {!busyClean && !storiesMd && (
                  <EmptyHint step="stories" />
                )}

                {!busyClean && storiesMd && (
                  <ResultDocument
                    stage="stories"
                    markdown={storiesMd}
                  />
                )}
              </TabsContent>

              <TabsContent
                value="gap"
                className="cs-tab-content"
                data-testid="panel-gap"
              >
                {busyAnalyze && (
                  <PipelineLoader
                    label="Auditing gaps and conflicts"
                    stage="03"
                    testId="loader-gap"
                  />
                )}

                {!busyAnalyze && !gapMd && (
                  <EmptyHint step="gap" />
                )}

                {!busyAnalyze && gapMd && (
                  <ResultDocument
                    stage="gap"
                    markdown={gapMd}
                  />
                )}
              </TabsContent>

              <TabsContent
                value="trace"
                className="cs-tab-content"
                data-testid="panel-trace"
              >
                {busyTrace && (
                  <PipelineLoader
                    label="Building technical traceability"
                    stage="04"
                    testId="loader-trace"
                  />
                )}

                {!busyTrace && !traceMd && (
                  <EmptyHint step="trace" />
                )}

                {!busyTrace && traceMd && (
                  <ResultDocument
                    stage="trace"
                    markdown={traceMd}
                    needsReview={traceNeedsReview}
                  />
                )}
              </TabsContent>
            </div>
          </Tabs>
        </section>
      </div>
    </div>
  );
}

function HistoryPanel({
  history,
  historyId,
  fmtDate,
  onOpen,
  onRemove,
  onReset,
  className = "",
}) {
  return (
    <aside className={`cs-history-panel ${className}`}>
      <div className="cs-history-panel__heading">
        <div>
          <History size={15} />
          <span>HISTORY</span>
          <span className="cs-history-panel__count">
            {String(history.length).padStart(2, "0")}
          </span>
        </div>

        <button
          type="button"
          data-testid="new-record-button"
          onClick={onReset}
          className="cs-new-button"
        >
          <Plus size={14} />
          NEW
        </button>
      </div>

      <div className="cs-history-panel__list">
        {history.length === 0 ? (
          <div className="cs-history-empty">
            <span className="cs-history-empty__icon">
              <History size={20} />
            </span>
            <strong>NO RECORDS</strong>
            <span>Run the pipeline to create your first trace.</span>
          </div>
        ) : (
          history.map((item, index) => (
            <article
              key={item.id}
              className={`cs-history-item ${
                historyId === item.id ? "is-active" : ""
              }`}
            >
              <button
                type="button"
                data-testid={`history-item-${item.id}`}
                className="cs-history-item__open"
                onClick={() => onOpen(item.id)}
              >
                <span className="cs-history-item__index">
                  {String(index + 1).padStart(2, "0")}
                </span>

                <span className="cs-history-item__body">
                  <span className="cs-history-item__title">
                    {item.title}
                  </span>

                  <span className="cs-history-item__meta">
                    <span className="cs-history-item__domain">
                      {item.domain}
                    </span>
                    <span>{fmtDate(item.created_at)}</span>
                  </span>
                </span>
              </button>

              <button
                type="button"
                className="cs-history-item__delete"
                aria-label={`Delete ${item.title}`}
                onClick={(event) =>
                  onRemove(item.id, event)
                }
              >
                <Trash2 size={14} />
              </button>
            </article>
          ))
        )}
      </div>

      <div className="cs-history-panel__footer">
        <span className="cs-history-panel__status-dot" />
        MONGODB ATLAS / SYNCED
      </div>
    </aside>
  );
}

function ResultDocument({
  stage,
  markdown,
  needsReview = false,
}) {
  return (
    <article
      className={`cs-result-document ${
        needsReview ? "has-review" : ""
      }`}
    >
      <div className="cs-result-document__rail">
        <span>{stage.toUpperCase()}</span>

        {needsReview ? (
          <span className="cs-result-document__review-badge">
            <AlertTriangle size={13} />
            REVIEW REQUIRED
          </span>
        ) : (
          <span className="cs-result-document__validated-badge">
            <CheckCircle2 size={13} />
            VALIDATED
          </span>
        )}
      </div>

      <div className="cs-result-document__markdown">
        <Markdown testId={`${stage}-md`}>
          {markdown}
        </Markdown>
      </div>
    </article>
  );
}

function PipelineLoader({
  label,
  stage,
  testId,
}) {
  return (
    <div
      className="cs-pipeline-loader"
      data-testid={testId}
      role="status"
      aria-live="polite"
    >
      <div className="cs-pipeline-loader__top">
        <div className="cs-pipeline-loader__identity">
          <span className="cs-pipeline-loader__stage">
            {stage}
          </span>

          <div>
            <span className="cs-pipeline-loader__eyebrow">
              CLEARSPEC AI PROCESS
            </span>
            <strong>{label}</strong>
          </div>
        </div>

        <span className="cs-pipeline-loader__active">
          <span />
          ACTIVE
        </span>
      </div>

      <div className="cs-pipeline-loader__scanner">
        <span />
      </div>

      <div className="cs-pipeline-loader__steps">
        <div>
          <span className="cs-pipeline-loader__chevron">
            &gt;
          </span>
          Parsing validated input stream
        </div>
        <div>
          <span className="cs-pipeline-loader__chevron">
            &gt;
          </span>
          Invoking OpenRouter inference
        </div>
        <div>
          <span className="cs-pipeline-loader__chevron">
            &gt;
          </span>
          Running deterministic output checks
        </div>
      </div>

      <div className="cs-pipeline-loader__foot">
        <span>MODEL</span>
        <strong>OPENAI / GPT-OSS-20B</strong>
        <span>VALIDATOR</span>
        <strong>ONLINE</strong>
      </div>
    </div>
  );
}

function EmptyHint({ step }) {
  const hint = HINTS[step];

  return (
    <div className="cs-empty-state">
      <div className="cs-empty-state__index">
        <span>{hint.n}</span>
        <span>{hint.eyebrow}</span>
      </div>

      <h1>{hint.t}</h1>

      <p>{hint.d}</p>

      <div className="cs-empty-state__terminal">
        <span className="cs-empty-state__prompt">
          CLEARSPEC://
        </span>
        <span>AWAITING SOURCE INPUT</span>
        <span className="cs-empty-state__cursor" />
      </div>

      <div className="cs-empty-state__grid">
        <div>
          <span>INPUT</span>
          <strong>STAKEHOLDER MATERIAL</strong>
        </div>
        <div>
          <span>ENGINE</span>
          <strong>VALIDATED AI PIPELINE</strong>
        </div>
        <div>
          <span>OUTPUT</span>
          <strong>REVIEWABLE ARTIFACT</strong>
        </div>
      </div>
    </div>
  );
}