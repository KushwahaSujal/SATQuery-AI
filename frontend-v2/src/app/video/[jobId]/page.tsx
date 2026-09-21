"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Loader2, ArrowLeft, Clock3, Cpu, AlertCircle } from "lucide-react";

const ACTIVE = new Set([
  "CREATED", "UPLOADED", "QUEUED", "PENDING", "VALIDATING",
  "PLANNING", "RUNNING", "GENERATING_EVIDENCE",
]);

function time(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${(seconds % 60).toFixed(1).padStart(4, "0")}`;
}

export default function VideoJobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const query = useQuery({
    queryKey: ["video-job", jobId],
    queryFn: () => api.videoJob(jobId),
    enabled: Boolean(jobId),
    refetchInterval: (current) =>
      ACTIVE.has(current.state.data?.status || "") ? 2000 : false,
    retry: 3,
  });

  const result = query.data;
  const metadata = result?.video_metadata;
  const flags = result?.flags || [];
  const duration = metadata?.duration_sec || 1;
  const status = result?.status || (query.isLoading ? "LOADING" : "UNKNOWN");
  const failed = status === "FAILED";

  return (
    <div className="h-screen overflow-hidden bg-[var(--canvas)] text-[var(--text)]">
      <TopBar showBrand />
      <div className="flex h-[calc(100vh-52px)] overflow-hidden">
        <Sidebar hideBrand />
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <header className="flex shrink-0 items-center gap-3 border-b border-[var(--border)] bg-[var(--surface)] px-5 py-3">
            <Link href="/history" className="flex h-7 w-7 items-center justify-center rounded-md border border-[var(--border)] text-[var(--text-2)]">
              <ArrowLeft className="h-3.5 w-3.5" />
            </Link>
            <div className="min-w-0">
              <p className="font-mono-data text-[10px] text-[var(--text-3)]">video intelligence / {jobId}</p>
              <h1 className="truncate text-sm font-semibold text-[var(--heading)]">{result?.query || "Video analysis"}</h1>
            </div>
            <span className="ml-auto rounded-full border border-[var(--border)] px-2.5 py-1 font-mono-data text-[10px] text-[var(--cyan)]">
              {status}
            </span>
          </header>

          <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_320px]">
            <section className="flex min-h-0 flex-col overflow-hidden border-r border-[var(--border)]">
              <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-2.5">
                <span className="font-mono-data text-[10px] uppercase tracking-wider text-[var(--text-3)]">Video feed</span>
                <span className="font-mono-data text-[10px] text-[var(--text-3)]">{metadata?.codec || "—"}</span>
              </div>
              <div className="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden bg-black">
                {failed ? (
                  <div className="text-center text-sm text-[var(--error)]"><AlertCircle className="mx-auto mb-2 h-6 w-6" />{result?.errors?.[0] || "Video analysis failed"}</div>
                ) : result ? (
                  <video src={api.videoStreamUrl(jobId)} controls preload="metadata" className="h-full w-full object-contain" />
                ) : (
                  // No stream yet: draw an honest placeholder frame instead of
                  // leaving a tall dead black box.
                  <div className="flex h-full w-full flex-col items-center justify-center gap-2 border border-dashed border-[var(--border)] text-[var(--text-3)]">
                    {query.isLoading ? (
                      <>
                        <Loader2 className="h-6 w-6 animate-spin text-[var(--cyan)]" />
                        <span className="font-mono-data text-[10px] uppercase tracking-wider">Loading video feed</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="h-6 w-6" />
                        <span className="font-mono-data text-[10px] uppercase tracking-wider">No video stream for this job</span>
                      </>
                    )}
                  </div>
                )}
              </div>
              <div className="border-t border-[var(--border)] bg-[var(--surface)] p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-mono-data text-[10px] uppercase tracking-wider text-[var(--text-3)]">Event timeline</span>
                  <span className="font-mono-data text-[10px] text-[var(--text-3)]">0:00 → {time(duration)}</span>
                </div>
                <div className="relative h-1.5 rounded-full bg-[var(--surface-2)]">
                  {flags.map((flag) => (
                    <span key={flag.flag_id} title={flag.label} className="absolute -top-0.5 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-[var(--cyan)]" style={{ left: `${Math.min(flag.start_timestamp / duration * 100, 98)}%` }} />
                  ))}
                </div>
              </div>
            </section>

            <aside className="flex min-h-0 flex-col overflow-hidden bg-[var(--surface)]">
              <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
                <span className="font-mono-data text-[10px] uppercase tracking-wider text-[var(--text-3)]">Detected events</span>
                <span className="font-mono-data text-[10px] text-[var(--text-3)]">{flags.length}</span>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto">
                {flags.length ? flags.map((flag) => (
                  <article key={flag.flag_id} className="border-b border-[var(--border)] p-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-xs font-medium text-[var(--heading)]">{flag.label}</span>
                      <span className="font-mono-data text-[10px] text-[var(--cyan)]">{flag.event_score.toFixed(2)}</span>
                    </div>
                    <p className="mt-1 flex items-center gap-1 text-[10px] text-[var(--text-3)]"><Clock3 className="h-3 w-3" />{time(flag.start_timestamp)} → {time(flag.end_timestamp)}</p>
                    <p className="mt-2 text-[11px] leading-relaxed text-[var(--text-2)]">{flag.reason}</p>
                  </article>
                )) : (
                  <div className="p-5 text-center text-xs text-[var(--text-3)]">
                    {ACTIVE.has(status) ? "Detection is still running…" : result?.workflow_reason || "No events detected"}
                  </div>
                )}
              </div>
              <div className="shrink-0 border-t border-[var(--border)] p-4">
                <p className="mb-2 flex items-center gap-1.5 font-mono-data text-[10px] uppercase tracking-wider text-[var(--text-3)]"><Cpu className="h-3 w-3" />Models executed</p>
                {(result?.models_used || ["grounding_dino", "sam2"]).map((model) => <p key={model} className="py-0.5 font-mono-data text-[10px] text-[var(--text-2)]">○ {model}</p>)}
              </div>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}
