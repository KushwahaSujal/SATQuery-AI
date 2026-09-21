"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BookOpen,
  Boxes,
  Braces,
  Check,
  FileText,
  Filter,
  Route,
  Satellite,
  Search,
  X,
} from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { api } from "@/lib/api";

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.05, delayChildren: 0.04 } } };
const itemVariant = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } },
};

type DocCategory = "All" | "Start" | "Backend" | "Frontend" | "API" | "Models" | "Operations" | "Project";

interface DocResource {
  title: string;
  path: string;
  category: Exclude<DocCategory, "All">;
  summary: string;
  tags: string[];
  status: "Authoritative" | "Live State" | "Reference" | "Research" | "Setup";
  sections: string;
  searchText?: string;
}

const hiddenDocumentPaths = new Set([
  ".commandcode/taste/taste.md",
  ".commandcode/taste/user-taste-profile/taste.md",
  ".pytest_cache/README.md",
  "frontend-v2/.commandcode/taste/taste.md",
  "frontend-v2/.commandcode/taste/user-taste-profile/taste.md",
  "frontend/AGENTS.md",
  "frontend/CLAUDE.md",
  "frontend/README.md",
  "frontend/SATQUERY_AI_FRONTEND_API_CONTRACT.md",
  "frontend/FRONTEND_POLISH.md",
  "frontend/SatQuery_FRONTEND_POLISH_2026-09-14.md",
  "project/handoff/ask-ayushman.md",
  "project/handoff/ppt-assets/README.md",
  "project/handoff/ppt-results.md",
  "project/memory.md",
  "project/plan-2026-09-14-agent-parity-geo.md",
  "project/split-ushnik-ayushman.md",
  "project/tasks.md",
  "project/decisions.md",
  "project/design.md",
  "project/phases.md",
  "project/prd.md",
  "project/qna.md",
  "project/restructure.md",
  "project/rules.md",
  "third_party/GeoChat/README.md",
  "third_party/GeoChat/docs/Customize_Component.md",
  "third_party/GeoChat/docs/Data.md",
  "third_party/GeoChat/docs/Evaluation.md",
  "third_party/GeoChat/docs/LoRA.md",
  "third_party/GeoChat/docs/MODEL_ZOO.md",
]);

const categories: DocCategory[] = ["All", "Start", "Backend", "Frontend", "API", "Models", "Operations", "Project"];

const docResources: DocResource[] = [
  {
    title: "Master Technical Documentation",
    path: "docs/SATQUERY_AI_MASTER_DOCUMENTATION.md",
    category: "Backend",
    summary: "Full product specification covering architecture, model strategy, workflows, deployment, mentor-defense notes, and scientific constraints.",
    tags: ["architecture", "models", "specification", "deployment"],
    status: "Authoritative",
    sections: "29 major sections",
  },
  {
    title: "Frontend API Contract",
    path: "docs/SATQUERY_AI_FRONTEND_API_CONTRACT.md",
    category: "API",
    summary: "The UI integration source of truth: model inventory, upload, analyze, visual analytics, video APIs, error codes, and JSON schemas.",
    tags: ["api", "schemas", "frontend", "errors"],
    status: "Authoritative",
    sections: "7 contract areas",
  },
  {
    title: "Teammate Setup Guide",
    path: "docs/SATQUERY_AI_TEAMMATE_SETUP.md",
    category: "Operations",
    summary: "Reproducible setup for hardware, environment variables, checkpoints, Docker, database, frontend, backend, smoke tests, and troubleshooting.",
    tags: ["setup", "docker", "checkpoints", "postgres"],
    status: "Setup",
    sections: "47 setup sections",
  },
  {
    title: "Model Data Setup",
    path: "docs/SATQUERY_AI_MODEL_DATA_SETUP.md",
    category: "Operations",
    summary: "Checkpoint and dataset placement rules for Grounding DINO, SAM 2.1, ChangeFormer, CDVQA, DOFA, RemoteCLIP, BigEarthNet, and fusion weights.",
    tags: ["checkpoints", "datasets", "weights"],
    status: "Setup",
    sections: "model assets",
  },
  {
    title: "Architecture Reality Map",
    path: "project/architecture.md",
    category: "Backend",
    summary: "Code-first architecture reference for FastAPI, orchestration, model adapters, workflows, DB schema, request lifecycle, and deployment topology.",
    tags: ["backend", "flow", "database", "orchestration"],
    status: "Live State",
    sections: "6 verified sections",
  },
  {
    title: "Execution Flow Map",
    path: "project/flow.md",
    category: "Backend",
    summary: "Call-chain walkthrough for POST /api/analyze, tool fan-out, grounding, video, visual analytics, known traps, and session changes.",
    tags: ["agent", "routing", "trace", "tools"],
    status: "Live State",
    sections: "8 flow sections",
  },
  {
    title: "Pre-Demo Baseline",
    path: "project/pre-demo.md",
    category: "Project",
    summary: "Measured readiness record with working features, blockers, demo caveats, browser verification notes, and honest scorecards.",
    tags: ["demo", "verification", "blockers", "metrics"],
    status: "Live State",
    sections: "measured baseline",
  },
  {
    title: "Frontend Guide",
    path: "frontend/FRONTEND_GUIDE.md",
    category: "Frontend",
    summary: "Frontend architecture, design tokens, pages, components, data flow, React Query usage, caching, accessibility, and development commands.",
    tags: ["nextjs", "react", "design system", "components"],
    status: "Reference",
    sections: "12 frontend sections",
  },
  {
    title: "Frontend Polish Handoff",
    path: "frontend/FRONTEND_POLISH.md",
    category: "Frontend",
    summary: "Known UI polish, backend-contract mismatches, dead controls, logic errors, visual issues, and frontend feature planning notes.",
    tags: ["ui", "contract", "polish", "bugs"],
    status: "Reference",
    sections: "7 audit sections",
  },
  {
    title: "Frontend V2 Demo Run",
    path: "frontend-v2/DEMO_RUN.md",
    category: "Frontend",
    summary: "Three-command end-to-end demo instructions, backend smoke test, UI verification path, layer viewer checks, and failure triage.",
    tags: ["frontend-v2", "demo", "smoke test"],
    status: "Setup",
    sections: "4 verification steps",
  },
  {
    title: "Model Dossier Index",
    path: "docs/models/README.md",
    category: "Models",
    summary: "Index for every model dossier, grouped by grounding, segmentation, change analysis, multisensor fusion, VLMs, and evaluated candidates.",
    tags: ["models", "research", "index"],
    status: "Research",
    sections: "27 dossier links",
  },
  {
    title: "Model Pipeline Architecture",
    path: "docs/models/MODEL_PIPELINE_ARCHITECTURE.md",
    category: "Models",
    summary: "Pipeline diagrams and step-level model interaction for object grounding, change detection, optical-SAR fusion, and video patrol.",
    tags: ["pipeline", "grounding", "change", "video"],
    status: "Research",
    sections: "5 pipelines",
  },
  {
    title: "Model Comparison Matrix",
    path: "docs/models/MODEL_COMPARISON_MATRIX.md",
    category: "Models",
    summary: "Active model matrix, evaluated candidates, historical strategies, compute footprint, and high-level selection comparison.",
    tags: ["matrix", "benchmarks", "selection"],
    status: "Research",
    sections: "3 matrices",
  },
  {
    title: "Training Status",
    path: "docs/models/MODEL_TRAINING_STATUS.md",
    category: "Models",
    summary: "Training status table and in-house CDVQA details, including measured adaptation evidence and checkpoint provenance.",
    tags: ["training", "cdvqa", "status"],
    status: "Research",
    sections: "training table",
  },
  {
    title: "Root README",
    path: "README.md",
    category: "Start",
    summary: "Project overview, key capabilities, quick start for Postgres, backend, frontend, tests, and canonical documentation links.",
    tags: ["quick start", "overview", "readme"],
    status: "Reference",
    sections: "quick start",
  },
  {
    title: "Fresh Clone Demo Setup",
    path: "DEMO_SETUP.md",
    category: "Start",
    summary: "Fresh clone path for model weights, backend startup, frontend startup, and demo resources.",
    tags: ["demo", "clone", "setup"],
    status: "Setup",
    sections: "5 setup steps",
  },
  {
    title: "Decisions Log",
    path: "project/decisions.md",
    category: "Project",
    summary: "Engineering decisions, open findings, measured caveats, and places where code reality intentionally overrides older public docs.",
    tags: ["decisions", "risks", "truth"],
    status: "Live State",
    sections: "100+ decisions",
  },
  {
    title: "Development Phases",
    path: "project/phases.md",
    category: "Project",
    summary: "Roadmap from environment ground truth through model blockers, measurement, routing robustness, hardening, and conference paper work.",
    tags: ["roadmap", "phases", "planning"],
    status: "Live State",
    sections: "P0-P6",
  },
];

function normalized(text: string) {
  return text.toLowerCase();
}

function categoryForPath(path: string): Exclude<DocCategory, "All"> {
  if (path.startsWith("docs/models/")) return "Models";
  if (path.startsWith("frontend") || path.startsWith("frontend-v2/")) return "Frontend";
  if (path.startsWith("project/")) return "Project";
  if (path.includes("API") || path.includes("api")) return "API";
  if (path.includes("SETUP") || path.includes("DEMO")) return "Start";
  if (path.startsWith("backend/")) return "Backend";
  return "Operations";
}

function MarkdownPreview({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  let codeLines: string[] = [];
  let inCode = false;
  let codeLanguage = "";

  const inline = (value: string): ReactNode[] => {
    const parts = value.split(/(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|\[[^\]]+\]\([^)]+\))/g);
    return parts.map((part, index) => {
      if (part.startsWith("`") && part.endsWith("`")) {
        return <code key={index} className="rounded bg-[var(--surface-3)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--cyan)]">{part.slice(1, -1)}</code>;
      }
      if ((part.startsWith("**") && part.endsWith("**")) || (part.startsWith("__") && part.endsWith("__"))) {
        return <strong key={index} className="font-semibold text-[var(--heading)]">{part.slice(2, -2)}</strong>;
      }
      if ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_"))) {
        return <em key={index} className="italic text-[var(--text)]">{part.slice(1, -1)}</em>;
      }
      const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (link) {
        return <a key={index} href={link[2]} target="_blank" rel="noreferrer" className="font-medium text-[var(--cyan)] underline decoration-[var(--cyan)]/40 underline-offset-2 hover:text-[var(--primary-bright)]">{link[1]}</a>;
      }
      return part;
    });
  };

  const flushCode = () => {
    if (!codeLines.length) return;
    blocks.push(
      <div key={`code-${blocks.length}`} className="my-4 overflow-hidden rounded-lg border border-[var(--border)] bg-[#080e17] shadow-[var(--shadow-sm)]">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-3 py-1.5">
          <span className="font-mono text-[9px] uppercase tracking-wider text-[var(--text-3)]">{codeLanguage || "code"}</span>
          <span className="text-[9px] text-[var(--text-4)]">Markdown code block</span>
        </div>
        <pre className="overflow-x-auto p-4 font-mono text-[11px] leading-5 text-cyan-100"><code data-language={codeLanguage}>{codeLines.join("\n")}</code></pre>
      </div>,
    );
    codeLines = [];
  };

  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (line.trim().startsWith("```")) {
      if (inCode) flushCode();
      inCode = !inCode;
      codeLanguage = line.trim().slice(3);
      index += 1;
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      index += 1;
      continue;
    }
    if (!line.trim()) {
      blocks.push(<div key={`space-${index}`} className="h-2" />);
      index += 1;
      continue;
    }
    if (/^---+$/.test(line.trim())) {
      blocks.push(<hr key={index} className="my-5 border-[var(--border)]" />);
      index += 1;
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const styles = level === 1
        ? "mt-8 border-b border-[var(--border)] pb-2 text-2xl font-bold text-[var(--heading)]"
        : level === 2
          ? "mt-7 text-lg font-bold text-[var(--heading)]"
          : level === 3
            ? "mt-5 text-sm font-bold text-[var(--cyan)]"
            : "mt-4 text-xs font-semibold uppercase tracking-wide text-[var(--text-2)]";
      const Heading = level === 1 ? "h1" : level === 2 ? "h2" : level === 3 ? "h3" : "h4";
      blocks.push(<Heading key={index} className={styles}>{inline(heading[2])}</Heading>);
      index += 1;
      continue;
    }
    const listItem = line.match(/^(\s*)([-*]|\d+[.)])\s+(.+)$/);
    if (listItem) {
      const ordered = /^\d/.test(listItem[2]);
      const listItems: { text: string; indent: number }[] = [];
      while (index < lines.length) {
        const item = lines[index].match(/^(\s*)([-*]|\d+[.)])\s+(.+)$/);
        if (!item || /^\d/.test(item[2]) !== ordered) break;
        listItems.push({ text: item[3], indent: item[1].length });
        index += 1;
      }
      blocks.push(
        ordered
          ? <ol key={`list-${index}`} className="my-3 list-decimal space-y-1 pl-6 text-[12px] leading-6 text-[var(--text-2)]">{listItems.map((item, itemIndex) => <li key={itemIndex} className={item.indent > 0 ? "ml-4" : ""}>{inline(item.text)}</li>)}</ol>
          : <ul key={`list-${index}`} className="my-3 space-y-1 text-[12px] leading-6 text-[var(--text-2)]">{listItems.map((item, itemIndex) => {
            const task = item.text.match(/^\[([ xX])\]\s+(.+)$/);
            return <li key={itemIndex} className={`flex gap-2 ${item.indent > 0 ? "ml-5" : ""}`}><span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${task?.[1].toLowerCase() === "x" ? "bg-[var(--green)]" : "bg-[var(--cyan)]"}`} />{task ? <span className={task[1].toLowerCase() === "x" ? "text-[var(--text-3)] line-through" : ""}>{inline(task[2])}</span> : <span>{inline(item.text)}</span>}</li>;
          })}</ul>,
      );
      continue;
    }
    if (line.trim().startsWith(">")) {
      const quoteLines: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith(">")) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(<blockquote key={`quote-${index}`} className="my-4 border-l-2 border-[var(--cyan)] bg-[var(--cyan-glow)]/40 px-4 py-2 text-[12px] italic leading-6 text-[var(--text-2)]">{quoteLines.map((quoteLine, quoteIndex) => <p key={quoteIndex}>{inline(quoteLine)}</p>)}</blockquote>);
      continue;
    }
    if (line.trim().startsWith("|")) {
      const tableLines: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        tableLines.push(lines[index]);
        index += 1;
      }
      const rows = tableLines
        .filter((tableLine) => !/^\s*\|?[\s:-]+(?:\|[\s:-]+)+\|?\s*$/.test(tableLine))
        .map((tableLine) => tableLine.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim()));
      blocks.push(
        <div key={`table-${index}`} className="my-4 overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="min-w-full border-collapse text-left text-[11px]">
            <thead className="bg-[var(--surface-3)] text-[var(--heading)]"><tr>{(rows[0] ?? []).map((cell, cellIndex) => <th key={cellIndex} className="border-b border-[var(--border)] px-3 py-2 font-semibold whitespace-nowrap">{inline(cell)}</th>)}</tr></thead>
            <tbody>{rows.slice(1).map((row, rowIndex) => <tr key={rowIndex} className="odd:bg-[var(--surface-2)] even:bg-[var(--surface)]">{row.map((cell, cellIndex) => <td key={cellIndex} className="border-b border-[var(--border)] px-3 py-2 align-top leading-5 text-[var(--text-2)]">{inline(cell)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      );
      continue;
    }
    blocks.push(<p key={index} className="text-[12px] leading-6 text-[var(--text-2)]">{inline(line)}</p>);
    index += 1;
  }
  if (inCode) flushCode();
  return <article className="documentation-markdown max-w-none">{blocks}</article>;
}

function statusClass(status: DocResource["status"]) {
  switch (status) {
    case "Authoritative":
      return "border-[var(--green)]/25 bg-[var(--green-bg)] text-[var(--green)]";
    case "Live State":
      return "border-[var(--amber)]/25 bg-[var(--amber-bg)] text-[var(--amber)]";
    case "Research":
      return "border-[var(--primary)]/25 bg-[var(--primary-glow)] text-[var(--primary-bright)]";
    case "Setup":
      return "border-[var(--cyan)]/25 bg-[var(--cyan-glow)] text-[var(--cyan)]";
    default:
      return "border-[var(--border)] bg-[var(--surface-3)] text-[var(--text-2)]";
  }
}

export default function DocumentationPage() {
  const [activeCategory, setActiveCategory] = useState<DocCategory>("All");
  const [searchDoc, setSearchDoc] = useState("");
  const [selectedDocPath, setSelectedDocPath] = useState(docResources[1].path);
  const [repositoryDocs, setRepositoryDocs] = useState<DocResource[]>([]);
  const [documentContent, setDocumentContent] = useState("");
  const [contentLoading, setContentLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [readerOpen, setReaderOpen] = useState(false);
  const contentScrollRef = useRef<HTMLElement>(null);
  const documentCache = useRef(new Map<string, string>());
  const documentRequests = useRef(new Map<string, Promise<string>>());

  useEffect(() => {
    let cancelled = false;
    api.documentation().then(({ documents }) => {
      if (cancelled) return;
      setRepositoryDocs(documents.map((doc) => ({
        title: doc.title,
        path: doc.path,
        category: categoryForPath(doc.path),
        summary: doc.summary,
        tags: [categoryForPath(doc.path).toLowerCase(), "markdown", "repository"],
        status: doc.path.startsWith("project/") ? "Live State" : "Reference",
        sections: `${doc.sections} sections`,
        searchText: doc.search_text,
      })));
    }).catch(() => {
      // The curated index remains available when the backend is offline.
    });
    return () => { cancelled = true; };
  }, []);

  const allDocs = useMemo(() => {
    // Curated metadata is intentionally authoritative and this ordering is load-bearing.
    // The backend index only derives a thin summary and a path-based status, so curated
    // entries are seeded first and never overwritten by a discovered copy of the same path.
    // Backend-only documents are still appended, and searchText is adopted because full-text
    // search data exists only on the discovered entries.
    const merged = new Map<string, DocResource>(docResources.map((doc) => [doc.path, doc] as const));
    for (const discovered of repositoryDocs) {
      const curated = merged.get(discovered.path);
      if (!curated) {
        merged.set(discovered.path, discovered);
        continue;
      }
      merged.set(discovered.path, { ...curated, searchText: discovered.searchText ?? curated.searchText });
    }
    return Array.from(merged.values()).filter((doc) => !hiddenDocumentPaths.has(doc.path));
  }, [repositoryDocs]);

  const filteredDocs = useMemo(() => {
    const q = normalized(searchDoc.trim());
    return allDocs.filter((doc) => {
      const categoryMatch = activeCategory === "All" || doc.category === activeCategory;
      if (!q) return categoryMatch;
      const haystack = normalized([doc.title, doc.path, doc.summary, doc.category, doc.status, ...doc.tags, doc.searchText ?? ""].join(" "));
      return categoryMatch && haystack.includes(q);
    });
  }, [activeCategory, allDocs, searchDoc]);

  const counts = useMemo(() => {
    return categories.reduce<Record<DocCategory, number>>((acc, category) => {
      acc[category] = category === "All" ? allDocs.length : allDocs.filter((doc) => doc.category === category).length;
      return acc;
    }, {} as Record<DocCategory, number>);
  }, [allDocs]);

  const selectedDoc = allDocs.find((doc) => doc.path === selectedDocPath) ?? filteredDocs[0] ?? allDocs[0] ?? docResources[1];
  const loadDocument = (path: string) => {
    const cached = documentCache.current.get(path);
    if (cached !== undefined) return Promise.resolve(cached);

    const pending = documentRequests.current.get(path);
    if (pending) return pending;

    const request = api.documentationContent(path).then(({ content }) => {
      documentCache.current.set(path, content);
      documentRequests.current.delete(path);
      return content;
    }).catch((error) => {
      documentRequests.current.delete(path);
      throw error;
    });
    documentRequests.current.set(path, request);
    return request;
  };

  const prefetchDocument = (path: string) => {
    if (documentCache.current.has(path) || documentRequests.current.has(path)) return;
    void loadDocument(path).catch(() => undefined);
  };

  const selectDocument = (path: string) => {
    const cached = documentCache.current.get(path);
    setSelectedDocPath(path);
    setReaderOpen(true);

    if (cached !== undefined) {
      setDocumentContent(cached);
      setContentLoading(false);
    } else {
      setContentLoading(true);
      loadDocument(path)
        .then((content) => {
          setDocumentContent(content);
          setContentLoading(false);
        })
        .catch(() => {
          setDocumentContent("");
          setContentLoading(false);
        });
    }
  };

  useEffect(() => {
    let cancelled = false;
    const cached = documentCache.current.get(selectedDoc.path);
    if (cached !== undefined) {
      setDocumentContent(cached);
      setContentLoading(false);
      return () => { cancelled = true; };
    }
    setContentLoading(true);
    loadDocument(selectedDoc.path)
      .then((content) => { if (!cancelled) setDocumentContent(content); })
      .catch(() => { if (!cancelled) setDocumentContent(""); })
      .finally(() => { if (!cancelled) setContentLoading(false); });
    return () => { cancelled = true; };
  }, [selectedDoc.path]);

  const copyDocument = async () => {
    if (!documentContent) return;
    await navigator.clipboard.writeText(documentContent);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="bg-[var(--canvas)] text-[var(--text)] font-sans antialiased h-screen overflow-hidden flex flex-col selection:bg-[var(--cyan)]/30 selection:text-[var(--canvas)]"
    >
      <TopBar showBrand={true} searchPlaceholder="Search docs, models, endpoints, workflows, or setup..." onSearch={(q) => setSearchDoc(q)} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar hideBrand={true} activeItem="documentation" className="h-full" />

        <main ref={contentScrollRef} className="flex-1 overflow-y-auto scroll-smooth" data-purpose="documentation-content">
          <div className="px-6 py-5">
            <div className="max-w-[1480px] mx-auto">
              <section className="space-y-5">
                <section className="border border-[var(--border)] bg-[var(--surface)] rounded-xl overflow-hidden shadow-lg" data-purpose="documentation-hero">
                  <div className="relative min-h-[260px] p-6 lg:p-7 overflow-hidden">
                    <div className="absolute inset-0 sat-preview-delhi-main opacity-40" />
                    <div className="absolute inset-0 bg-gradient-to-r from-[var(--surface)] via-[var(--surface)]/92 to-[var(--surface)]/52" />
                    <div className="absolute right-8 top-8 hidden lg:block text-[var(--cyan)]/80">
                      <Satellite className="h-28 w-28 drop-shadow-[0_0_24px_rgba(0,194,168,0.30)]" strokeWidth={1.4} />
                    </div>

                    <div className="relative z-10 max-w-3xl">
                      <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-[var(--cyan-glow)] border border-[var(--cyan)]/30 text-[var(--cyan)] text-[10px] font-semibold uppercase tracking-wider mb-4">
                        <BookOpen className="h-3.5 w-3.5" />
                        Repo-backed documentation hub
                      </div>
                      <h1 className="text-2xl lg:text-4xl font-bold text-[var(--heading)] tracking-tight leading-tight">SatQuery AI Documentation</h1>
                      <p className="text-sm text-[var(--text-2)] mt-3 leading-relaxed max-w-2xl">
                        A professional index of the backend, frontend, API contract, model dossiers, setup guides, verification notes, and known caveats already present across the repository markdown files.
                      </p>

                      <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                          { label: "Markdown files indexed", value: String(allDocs.length), icon: FileText },
                          { label: "Model dossiers", value: "27", icon: Boxes },
                          { label: "API endpoint groups", value: "8", icon: Braces },
                          { label: "Workflow families", value: "5", icon: Route },
                        ].map((metric) => {
                          const Icon = metric.icon;
                          return (
                            <div key={metric.label} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)]/85 p-3">
                              <Icon className="h-4 w-4 text-[var(--cyan)] mb-2" />
                              <div className="text-lg font-bold text-[var(--heading)] leading-none">{metric.value}</div>
                              <div className="text-[10px] text-[var(--text-3)] mt-1 leading-snug">{metric.label}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </section>

                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                  <div className="flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
                    <div className="relative flex-1 min-w-0 lg:min-w-[16rem]">
                      <Search className="h-4 w-4 text-[var(--text-3)] absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        value={searchDoc}
                        onChange={(e) => setSearchDoc(e.target.value)}
                        className="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg pl-9 pr-3 py-2 text-xs text-[var(--text)] placeholder:text-[var(--text-3)] focus:outline-none focus:border-[var(--cyan)]"
                        placeholder="Search by endpoint, model, guide, status, or file path..."
                        type="text"
                      />
                      {searchDoc && (
                        <button
                          type="button"
                          onClick={() => setSearchDoc("")}
                          aria-label="Clear documentation search"
                          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-[var(--text-3)] hover:bg-[var(--surface-3)] hover:text-[var(--heading)]"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                    <div className="flex min-w-0 items-center gap-2 overflow-x-auto pb-1 lg:pb-0">
                      <Filter className="h-4 w-4 text-[var(--text-3)] shrink-0" />
                      {categories.map((category) => {
                        const active = activeCategory === category;
                        return (
                          <button
                            key={category}
                            onClick={() => setActiveCategory(category)}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition whitespace-nowrap ${
                              active
                                ? "bg-[var(--cyan-glow)] border-[var(--cyan)]/50 text-[var(--cyan)]"
                                : "bg-[var(--surface-2)] border-[var(--border)] text-[var(--text-2)] hover:border-[var(--border-strong)]"
                            }`}
                          >
                            <span>{category}</span>
                            <span className="text-[10px] opacity-70">{counts[category]}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </section>

                {readerOpen && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--scrim)] p-3 sm:p-6 lg:p-10" data-purpose="documentation-reader-overlay">
                <section className="flex max-h-full w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-[var(--cyan)]/40 bg-[var(--surface)] shadow-[var(--shadow-xl)]" data-purpose="live-markdown-reader">
                  <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 shrink-0 text-[var(--cyan)]" />
                        <h2 className="truncate text-sm font-bold text-[var(--heading)]">{selectedDoc.title}</h2>
                      </div>
                      <p className="mt-0.5 text-[10px] text-[var(--text-3)]">
                        {selectedDoc.summary}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="rounded-md border border-[var(--cyan)]/25 bg-[var(--cyan-glow)] px-2 py-1 font-mono text-[10px] text-[var(--cyan)]">
                        {contentLoading ? "Loading..." : `${documentContent.split(/\r?\n/).length} lines`}
                      </span>
                      <button
                        type="button"
                        onClick={copyDocument}
                        disabled={!documentContent || contentLoading}
                        className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[10px] font-semibold text-[var(--text-2)] transition hover:border-[var(--cyan)]/50 hover:text-[var(--cyan)] disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {copied ? <Check className="h-3 w-3 text-[var(--green)]" /> : <FileText className="h-3 w-3" />}
                        {copied ? "Copied" : "Copy"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setReaderOpen(false)}
                        aria-label="Close document reader"
                        className="inline-flex items-center justify-center rounded-md border border-[var(--border)] bg-[var(--surface)] p-1.5 text-[var(--text-2)] transition hover:border-[var(--cyan)]/50 hover:text-[var(--cyan)]"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
                    {contentLoading ? (
                      <div className="space-y-3 py-4">
                        {[80, 65, 90, 52].map((width) => <div key={width} style={{ width: `${width}%` }} className="h-3 animate-pulse rounded bg-[var(--surface-3)]" />)}
                      </div>
                    ) : documentContent ? (
                      <MarkdownPreview content={documentContent} />
                    ) : (
                      <div className="rounded-lg border border-dashed border-[var(--border)] p-8 text-center">
                        <FileText className="mx-auto mb-2 h-6 w-6 text-[var(--text-3)]" />
                        <p className="text-xs font-semibold text-[var(--heading)]">Document unavailable</p>
                        <p className="mt-1 text-[11px] text-[var(--text-3)]">Start the backend and select this document again.</p>
                      </div>
                    )}
                  </div>
                </section>
                  </div>
                )}

                <motion.section variants={stagger} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-2 gap-3.5" data-purpose="documentation-results">
                  {filteredDocs.map((doc) => (
                    <motion.article
                      key={doc.path}
                      variants={itemVariant}
                      role="button"
                      tabIndex={0}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => selectDocument(doc.path)}
                      onMouseEnter={() => prefetchDocument(doc.path)}
                      onFocus={() => prefetchDocument(doc.path)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          selectDocument(doc.path);
                        }
                      }}
                      className={`rounded-xl border bg-[var(--surface-2)] p-4 transition group cursor-pointer ${
                        selectedDoc.path === doc.path
                          ? "border-[var(--cyan)] shadow-[0_0_18px_rgba(0,194,168,0.16)]"
                          : "border-[var(--border)] hover:border-[var(--cyan)]/45"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-2">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-md border text-[9px] font-semibold uppercase tracking-wider ${statusClass(doc.status)}`}>{doc.status}</span>
                            <span className="text-[10px] text-[var(--text-3)]">{doc.category}</span>
                          </div>
                          <h2 className="text-sm font-semibold text-[var(--heading)] group-hover:text-[var(--cyan)] transition-colors">{doc.title}</h2>
                          <p className="text-[11px] text-[var(--text-3)] mt-1.5 leading-relaxed">{doc.summary}</p>
                        </div>
                        <FileText className="h-4 w-4 text-[var(--text-3)] shrink-0 mt-1" />
                      </div>
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {doc.tags.map((tag) => (
                          <span key={tag} className="px-2 py-0.5 rounded-md bg-[var(--surface-3)] border border-[var(--border)] text-[10px] text-[var(--text-2)]">{tag}</span>
                        ))}
                      </div>
                      <div className="mt-3 pt-3 border-t border-[var(--border)] flex items-center justify-between gap-3">
                        <span className="font-mono text-[10px] text-[var(--text-3)] truncate" title={doc.path}>{doc.path}</span>
                        <span className="inline-flex items-center gap-1 text-[10px] text-[var(--cyan)] font-semibold shrink-0">
                          {selectedDoc.path === doc.path ? "Open now" : doc.sections}
                          <ArrowRight className="h-3 w-3" />
                        </span>
                      </div>
                    </motion.article>
                  ))}
                  {filteredDocs.length === 0 && (
                    <div className="md:col-span-2 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] p-8 text-center">
                      <Search className="h-8 w-8 text-[var(--text-3)] mx-auto mb-3" />
                      <h2 className="text-sm font-semibold text-[var(--heading)]">No documentation matched</h2>
                      <p className="text-xs text-[var(--text-3)] mt-1">Try a model name, endpoint, workflow, or broader category.</p>
                    </div>
                  )}
                </motion.section>
              </section>
            </div>
          </div>
        </main>
      </div>
    </motion.div>
  );
}
