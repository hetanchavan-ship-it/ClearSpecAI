import logo from "@/assets/clearspecAI-logo.png";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ChevronDown,
  FileUp,
  History,
  LogOut,
  Plus,
  Sparkles,
  Trash2,
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
import { ScanLoader } from "@/components/ui/ScanLoader";

const DOMAINS = [
  { value: "general", label: "General" },
  { value: "healthcare", label: "Healthcare" },
  { value: "finance", label: "Finance" },
  { value: "retail", label: "Retail" },
  { value: "logistics", label: "Logistics" },
  { value: "saas", label: "SaaS" },
];

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

  const [tab, setTab] = useState("stories");
  const [history, setHistory] = useState([]);

  const fileRef = useRef(null);

  const loadHistory = async () => {
    try {
      const items = await csApi.history();
      setHistory(items);
    } catch (error) {
      console.error("Could not load history:", error);
    }
  };

  useEffect(() => {
    void loadHistory();
   }, []);

  const resetWorkspace = () => {
    setHistoryId(null);
    setRawText("");
    setDomain("general");
    setContext("");
    setStoriesMd("");
    setGapMd("");
    setTraceMd("");
    setTab("stories");
  }; 
  const onClean = async () => {
    if (rawText.trim().length < 10) {
      toast.error("Add at least 10 characters of input.");
      return;
    }

    setBusyClean(true);
    setStoriesMd("");
    setGapMd("");
    setTraceMd("");
    setTab("stories");

    try {
      const { id, stories_md } = await csApi.clean({
        raw_text: rawText,
        domain,
      });

      setHistoryId(id);
      setStoriesMd(stories_md);
      setBusyClean(false);

      await loadHistory();

      // Run Gap Analysis
      setBusyAnalyze(true);

      const { gap_md } = await csApi.analyze({
        stories: stories_md,
        context,
        history_id: id,
      });

      setGapMd(gap_md);
      setBusyAnalyze(false);

      // Run Technical Trace
      setBusyTrace(true);

      const { trace_md } = await csApi.trace({
        stories: stories_md,
        history_id: id,
      });

      setTraceMd(trace_md);
      setBusyTrace(false);

      await loadHistory();

      toast.success("Pipeline complete.");
    } catch (error) {
      console.error(error);

      toast.error(
        error?.response?.data?.detail || "Pipeline failed."
      );

      setBusyAnalyze(false);
      setBusyTrace(false);
    } finally {
      setBusyClean(false);
    }
  };

  const onUpload = async (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    try {
      const { text, filename } = await csApi.extract(file);

      setRawText((previous) =>
        previous
          ? `${previous}

--- ${filename} ---
${text}`
          : text
      );

      toast.success(`Extracted from ${filename}`);
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          "Could not parse file."
      );
    } finally {
      event.target.value = "";
    }
  };

  const openHistory = async (id) => {
    try {
      const doc = await csApi.getHistory(id);

      setHistoryId(doc.id);

      setRawText(doc.raw_text);
      setDomain(doc.domain);

      setStoriesMd(doc.stories_md || "");
      setGapMd(doc.gap_md || "");
      setTraceMd(doc.trace_md || "");

      setTab("stories");
    } catch (error) {
      console.error(error);
      toast.error("Could not load record.");
    }
  };

  const removeHistory = async (id, event) => {
  event.stopPropagation();

    try {
      await csApi.deleteHistory(id);

      if (id === historyId) {
        resetWorkspace();
      }

      await loadHistory();
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

  return (
    <div className="h-screen w-screen flex flex-col bg-white text-gray-900 overflow-hidden">

      {/* ================= HEADER ================= */}

      <header className="h-14 border-b border-gray-200 flex items-center justify-between px-6 bg-white">

        <div className="flex items-center gap-3">

          <img
  src={logo}
  alt="ClearSpec AI Logo"
  className="h-8 w-auto object-contain"
/>

          <span className="font-mono text-xs uppercase tracking-overline">
            ClearSpec / AI
          </span>

          <span className="text-gray-300">|</span>

          <span className="hidden sm:inline text-xs font-mono uppercase tracking-overline text-gray-500">
            Requirement Engineering Workstation
          </span>

        </div>

        <DropdownMenu>

          <DropdownMenuTrigger asChild>

            <button
              data-testid="user-menu-button"
              className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 hover:bg-gray-50 transition-colors"
            >

              <div className="w-6 h-6 bg-klein text-white flex items-center justify-center text-xs font-mono">
                {user?.name?.[0]?.toUpperCase() || "U"}
              </div>

              <span className="text-sm font-mono">
                {user?.email}
              </span>

              <ChevronDown className="w-3.5 h-3.5 text-gray-500" />

            </button>

          </DropdownMenuTrigger>

          <DropdownMenuContent className="w-56 rounded-none border-gray-200">

            <DropdownMenuLabel className="font-mono text-xs uppercase tracking-overline text-gray-500">
              Signed In
            </DropdownMenuLabel>

            <DropdownMenuItem disabled className="font-mono text-xs">
              {user?.name}
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              data-testid="logout-menu-item"
              className="cursor-pointer rounded-none"
              onClick={() => {
                logout();
                nav("/login", { replace: true });
              }}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>

          </DropdownMenuContent>

        </DropdownMenu>

      </header>

      {/* ================= MAIN BODY ================= */}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[260px_1fr_1.2fr] overflow-hidden">
                {/* ================= SIDEBAR ================= */}

        <aside className="hidden lg:flex flex-col border-r border-gray-200 bg-[#FAFAF7]">

          <div className="h-12 px-4 border-b border-gray-200 flex items-center justify-between">

            <span className="flex items-center gap-2 text-xs font-mono uppercase tracking-overline text-gray-600">
              <History className="w-3.5 h-3.5" />
              History
            </span>

            <button
              data-testid="new-record-button"
              onClick={resetWorkspace}
              className="flex items-center gap-1 text-xs font-mono text-klein hover:underline"
            >
              <Plus className="w-3 h-3" />
              New
            </button>

          </div>

          <div className="flex-1 overflow-y-auto">

            {history.length === 0 ? (

              <div className="p-4 text-xs font-mono text-gray-400">
                No records yet. Run your first analysis →
              </div>

            ) : (

              history.map((item) => (

                <button
                  key={item.id}
                  data-testid={`history-item-${item.id}`}
                  onClick={() => openHistory(item.id)}
                  className={`group w-full border-b border-gray-200 p-3 text-left transition-colors hover:bg-white ${
                    historyId === item.id
                      ? "bg-white border-l-2 border-l-klein"
                      : ""
                  }`}
                >

                  <div className="flex items-start justify-between gap-2">

                    <div className="min-w-0 flex-1">

                      <div className="truncate text-sm text-gray-900">
                        {item.title}
                      </div>

                      <div className="mt-1 flex items-center gap-2">

                        <span className="border border-gray-200 px-1 text-[10px] font-mono uppercase tracking-overline text-klein">
                          {item.domain}
                        </span>

                        <span className="text-[11px] font-mono text-gray-400">
                          {fmtDate(item.created_at)}
                        </span>

                      </div>

                    </div>

                    <Trash2
                      className="w-3.5 h-3.5 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100"
                      onClick={(event) => removeHistory(item.id, event)}
                    />

                  </div>

                </button>

              ))

            )}

          </div>

        </aside>

        {/* ================= INPUT PANEL ================= */}

        <section className="flex flex-col border-r border-gray-200 overflow-hidden">

          <div className="h-12 border-b border-gray-200 px-6 flex items-center justify-between">

            <span className="text-xs font-mono uppercase tracking-overline text-gray-600">
              01 — Input
            </span>

            <span className="text-xs font-mono text-gray-400">
              {rawText.length} chars
            </span>

          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-5">

            <div className="grid grid-cols-2 gap-4">

              <div className="space-y-2">

                <Label className="text-xs font-mono uppercase tracking-overline text-gray-500">
                  Domain
                </Label>

                <Select
                  value={domain}
                  onValueChange={setDomain}
                >
                                      <SelectTrigger
                    data-testid="domain-select-trigger"
                    className="rounded-none border-gray-300 font-mono text-sm"
                  >
                    <SelectValue />
                  </SelectTrigger>

                  <SelectContent className="rounded-none">
                    {DOMAINS.map((item) => (
                      <SelectItem
                        key={item.value}
                        value={item.value}
                        data-testid={`domain-option-${item.value}`}
                        className="rounded-none font-mono text-sm"
                      >
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>

                </Select>

              </div>

              <div className="space-y-2">

                <Label className="text-xs font-mono uppercase tracking-overline text-gray-500">
                  Transcript (PDF / DOCX / TXT)
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
                  variant="outline"
                  data-testid="upload-button"
                  onClick={() => fileRef.current?.click()}
                  className="w-full h-10 justify-start rounded-none border-gray-300 font-mono text-sm hover:bg-gray-50"
                >
                  <FileUp className="mr-2 h-4 w-4" />
                  Upload file
                </Button>

              </div>

            </div>

            <div className="space-y-2">

              <Label className="text-xs font-mono uppercase tracking-overline text-gray-500">
                Raw stakeholder notes
              </Label>

              <Textarea
                data-testid="raw-text-input"
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder={`Paste meeting notes, emails, BRD snippets, voice transcripts...

Example:
"We need a portal where doctors can quickly view patient lab reports.
Patients should receive SMS or email notifications when reports are ready.
The system must support urgent reports and allow filtering by date."`}
                className="min-h-[280px] rounded-none border-gray-300 font-body text-sm focus-visible:border-[#002FA7] focus-visible:ring-1 focus-visible:ring-[#002FA7]"
              />

            </div>

            <div className="space-y-2">

              <Label className="text-xs font-mono uppercase tracking-overline text-gray-500">
                Existing system context (Optional)
              </Label>

              <Textarea
                data-testid="context-input"
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="Backlog snippets, existing workflows, technical constraints..."
                className="min-h-[110px] rounded-none border-gray-300 font-body text-sm focus-visible:border-[#002FA7] focus-visible:ring-1 focus-visible:ring-[#002FA7]"
              />

            </div>

          </div>

          <div className="border-t border-gray-200 bg-[#FAFAF7] p-4">

            <Button
              data-testid="run-pipeline-button"
              onClick={onClean}
              disabled={busyClean || busyAnalyze || busyTrace}
              className="h-12 w-full rounded-none bg-klein text-white hover:bg-[#00258A]"
            >
              <Sparkles className="mr-2 h-4 w-4" />

              {busyClean
                ? "Standardising..."
                : busyAnalyze
                ? "Analysing..."
                : busyTrace
                ? "Tracing..."
                : "Clean → Analyze → Trace"}

            </Button>
                        <p className="mt-2 text-center text-[11px] font-mono text-gray-400">
              Pipeline runs three stages sequentially · OpenRouter
            </p>

          </div>

        </section>

        {/* ================= RESULTS PANEL ================= */}

        <section className="flex flex-col overflow-hidden bg-white">

          <Tabs
            value={tab}
            onValueChange={setTab}
            className="flex h-full flex-col"
          >

            <div className="flex h-12 items-center justify-between border-b border-gray-200 pr-6">

              <TabsList className="h-12 gap-0 rounded-none bg-transparent p-0">

                <TabsTrigger
                  value="stories"
                  data-testid="tab-stories"
                  className="h-12 rounded-none border-b-2 border-transparent px-5 font-mono text-xs uppercase tracking-overline text-gray-500 data-[state=active]:border-klein data-[state=active]:bg-transparent data-[state=active]:text-gray-900 data-[state=active]:shadow-none"
                >
                  02 / Stories
                </TabsTrigger>

                <TabsTrigger
                  value="gap"
                  data-testid="tab-gap"
                  className="h-12 rounded-none border-b-2 border-transparent px-5 font-mono text-xs uppercase tracking-overline text-gray-500 data-[state=active]:border-klein data-[state=active]:bg-transparent data-[state=active]:text-gray-900 data-[state=active]:shadow-none"
                >
                  03 / Gap Analysis
                </TabsTrigger>

                <TabsTrigger
                  value="trace"
                  data-testid="tab-trace"
                  className="h-12 rounded-none border-b-2 border-transparent px-5 font-mono text-xs uppercase tracking-overline text-gray-500 data-[state=active]:border-klein data-[state=active]:bg-transparent data-[state=active]:text-gray-900 data-[state=active]:shadow-none"
                >
                  04 / Technical Trace
                </TabsTrigger>

              </TabsList>

              <span className="hidden text-[11px] font-mono text-gray-400 md:block">
                Powered by ClearSpec AI
              </span>

            </div>

            <div className="flex-1 overflow-y-auto p-8">

              <TabsContent
                value="stories"
                className="mt-0"
                data-testid="panel-stories"
              >

                {busyClean && (
                  <ScanLoader
                    label="Generating user stories"
                    testId="loader-stories"
                  />
                )}

                {!busyClean && !storiesMd && (
                  <EmptyHint step="stories" />
                )}

                {!busyClean && storiesMd && (
                  <Markdown testId="stories-md">
                    {storiesMd}
                  </Markdown>
                )}

              </TabsContent>

              <TabsContent
                value="gap"
                className="mt-0"
                data-testid="panel-gap"
              >

                {busyAnalyze && (
                  <ScanLoader
                    label="Auditing gaps & conflicts"
                    testId="loader-gap"
                  />
                )}

                {!busyAnalyze && !gapMd && (
                  <EmptyHint step="gap" />
                )}

                {!busyAnalyze && gapMd && (
                  <Markdown testId="gap-md">
                    {gapMd}
                  </Markdown>
                )}

              </TabsContent>

              <TabsContent
                value="trace"
                className="mt-0"
                data-testid="panel-trace"
              >

                {busyTrace && (
                  <ScanLoader
                    label="Drafting technical artifacts"
                    testId="loader-trace"
                  />
                )}

                {!busyTrace && !traceMd && (
                  <EmptyHint step="trace" />
                )}

                {!busyTrace && traceMd && (
                  <Markdown testId="trace-md">
                    {traceMd}
                  </Markdown>
                )}

              </TabsContent>

            </div>

          </Tabs>

        </section>

      </div>

    </div>

  );
}

/* ================= EMPTY STATE ================= */

const HINTS = {

  stories: {
    n: "02",
    t: "Standardised User Stories",
    d: "Paste raw stakeholder input on the left and run the pipeline. ClearSpec AI converts your notes into INVEST-compliant Agile user stories with clear acceptance criteria.",
  },

  gap: {
    n: "03",
    t: "Gap & Conflict Analysis",
    d: "Automatically detect ambiguity, missing requirements, contradictions, risks and unresolved stakeholder questions before development begins.",
  },

  trace: {
    n: "04",
    t: "Technical Traceability",
    d: "Generate database schema suggestions, REST APIs, business logic and implementation pseudocode directly from your approved user stories.",
  },

};

function EmptyHint({ step }) {

  const hint = HINTS[step];

  return (

    <div className="max-w-xl">

      <div className="mb-3 text-xs font-mono uppercase tracking-overline text-klein">
        Step {hint.n}
      </div>

      <div className="mb-3 font-heading text-4xl text-gray-900">
        {hint.t}
      </div>

      <p className="leading-relaxed text-gray-600">
        {hint.d}
      </p>

      <div className="mt-8 border border-dashed border-gray-300 p-6 font-mono text-sm text-gray-400">
        AWAITING INPUT // Run the pipeline to populate this panel.
      </div>

    </div>

  );

}
