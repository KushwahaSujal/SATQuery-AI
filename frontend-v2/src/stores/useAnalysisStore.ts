"use client";

import { create } from "zustand";
import { api } from "@/lib/api";
import { addLocalJob } from "@/lib/localJobs";
import type { AnalysisResult, UploadedRaster, UploadedVideo } from "@/lib/types";

const VIDEO_EXTENSIONS = new Set([".mp4", ".avi", ".mov", ".mkv", ".webm"]);

export type LiveJob = {
  job_id: string;
  status: string;
  task?: string;
  query?: string;
  progress?: number;
  execution_steps?: Record<string, unknown>[];
  models_used?: string[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  type?: "text" | "progress" | "result" | "error";
  images?: string[];
  result?: AnalysisResult;
};

export const RUNNING_STATUSES = new Set([
  "QUEUED", "CREATED", "UPLOADED", "VALIDATING",
  "PLANNING", "RUNNING", "GENERATING_EVIDENCE", "PENDING",
]);

let msgCounter = 0;
function nextMsgId() {
  return `msg-${Date.now()}-${++msgCounter}`;
}

function isVideoFile(file: File): boolean {
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  return VIDEO_EXTENSIONS.has(ext) || file.type.startsWith("video/");
}

interface AnalysisState {
  messages: ChatMessage[];
  rasters: UploadedRaster[];
  video: UploadedVideo | null;
  activeJobId: string | null;
  liveJob: LiveJob | null;
  liveResult: AnalysisResult | null;
  analysisError: string | null;
  isSubmittingAnalysis: boolean;
  uploadProgress: number | null;

  addMessage: (msg: Omit<ChatMessage, "id" | "timestamp">) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  handleUpload: (files: FileList) => Promise<void>;
  startAnalysis: (prompt: string, taskType?: string) => Promise<void>;
  resetAnalysis: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set, get) => ({
  messages: [],
  rasters: [],
  video: null,
  activeJobId: null,
  liveJob: null,
  liveResult: null,
  analysisError: null,
  isSubmittingAnalysis: false,
  uploadProgress: null,

  addMessage: (msg) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { ...msg, id: nextMsgId(), timestamp: Date.now() },
      ],
    })),

  updateMessage: (id, patch) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...patch } : m
      ),
    })),

  handleUpload: async (files) => {
    const fileList = Array.from(files);
    const videos = fileList.filter(isVideoFile);
    const images = fileList.filter((f) => !isVideoFile(f));

    set({ uploadProgress: 0 });

    try {
      if (images.length > 0) {
        const { rasters: uploaded } = await api.uploadRastersWithProgress(
          images,
          (pct) => set({ uploadProgress: pct }),
        );
        set((state) => ({ rasters: [...state.rasters, ...uploaded] }));
      }
      if (videos.length > 0) {
        const { video: uploaded } = await api.uploadVideoWithProgress(
          videos[0],
          (pct) => set({ uploadProgress: pct }),
        );
        set({ video: uploaded });
      }
      set({ uploadProgress: 100 });
      setTimeout(() => set({ uploadProgress: null }), 800);
    } catch {
      set({ uploadProgress: null });
    }
  },

  startAnalysis: async (prompt, taskType) => {
    const state = get();
    const promptText = prompt.trim();
    if (!promptText) return;

    const hasVideo = Boolean(state.video);

    const previews: string[] = [];
    if (hasVideo && state.video?.preview_url) {
      previews.push(state.video.preview_url);
    }
    state.rasters.forEach((r) => {
      if (r.preview_url) previews.push(r.preview_url);
    });

    set({ analysisError: null, liveResult: null, liveJob: null });

    set((s) => ({
      messages: [
        ...s.messages,
        {
          id: nextMsgId(),
          role: "user",
          content: promptText,
          timestamp: Date.now(),
          images: previews.length ? previews : undefined,
        },
        {
          id: nextMsgId(),
          role: "assistant",
          content: hasVideo ? "Analyzing your video..." : "Analyzing your imagery...",
          timestamp: Date.now() + 1,
          type: "progress",
        },
      ],
    }));

    set({ isSubmittingAnalysis: true });

    try {
      let response: { job_id: string };

      if (hasVideo && state.video) {
        response = await api.analyzeVideo({
          video_id: state.video.id,
          query: promptText,
        });
      } else {
        const requestId = state.rasters.find((r) => r.request_id)?.request_id;
        const imageFilenames = state.rasters.map((r) => r.filename).filter(Boolean);

        let resolvedTask: string | undefined;
        if (taskType && taskType !== "auto") {
          resolvedTask = taskType;
        } else {
          resolvedTask = "unsupported";
        }

        response = await api.analyze({
          query: promptText,
          request_id: requestId,
          image_filenames: imageFilenames,
          raster_ids: state.rasters.map((r) => r.id),
          task: resolvedTask as import("@/lib/types").TaskType | undefined,
        });
      }

      set({
        activeJobId: response.job_id,
        liveJob: {
          job_id: response.job_id,
          status: "QUEUED",
          query: promptText,
        },
      });

      addLocalJob({
        job_id: response.job_id,
        task: hasVideo ? "video_vqa" : state.rasters.length >= 2 ? "bi_temporal_change_vqa" : "auto",
        query: promptText,
        status: "QUEUED",
        created_at: new Date().toISOString(),
      });
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : "Unable to start analysis.";
      set({ analysisError: errMsg });
      const msgs = get().messages;
      const lastMsg = msgs[msgs.length - 1];
      if (lastMsg?.type === "progress") {
        get().updateMessage(lastMsg.id, {
          content: errMsg,
          type: "error",
        });
      }
    } finally {
      set({ isSubmittingAnalysis: false });
    }
  },

  resetAnalysis: () =>
    set({
      messages: [],
      rasters: [],
      video: null,
      activeJobId: null,
      liveJob: null,
      liveResult: null,
      analysisError: null,
      isSubmittingAnalysis: false,
      uploadProgress: null,
    }),
}));

export function formatPercent(value?: number) {
  if (value == null || Number.isNaN(value)) return null;
  const percent = value <= 1 ? value * 100 : value;
  return `${percent.toFixed(percent >= 10 ? 1 : 2)}%`;
}

export function formatArea(value?: number) {
  if (value == null || Number.isNaN(value)) return null;
  return `${value.toFixed(value >= 10 ? 1 : 2)} km²`;
}

export function traceLabel(step: { name?: unknown; step?: unknown; tool?: unknown }) {
  return String(step.name || step.step || step.tool || "Pipeline step");
}
