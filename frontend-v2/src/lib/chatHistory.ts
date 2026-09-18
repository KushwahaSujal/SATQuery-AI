export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string; // ISO
  kind?: "text" | "answer" | "evidence" | "thinking";
  meta?: {
    confidence?: number;
    workflow?: string;
    models_used?: string[];
    changed_pixels?: number;
    region_count?: number;
    area_km2?: number;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
  job_id?: string;
  status?:
    | "QUEUED"
    | "VALIDATING"
    | "PLANNING"
    | "RUNNING"
    | "GENERATING_EVIDENCE"
    | "COMPLETED"
    | "FAILED"
    | "IDLE";
}

const CHAT_HISTORY_KEY = "satquery.chat_history";
const ACTIVE_SESSION_KEY = "satquery.active_session";
const MAX_SESSIONS = 50;

function isClient() {
  return typeof window !== "undefined";
}

function safeRead<T>(key: string, fallback: T): T {
  if (!isClient()) return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function safeWrite(key: string, value: unknown) {
  if (!isClient()) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // quota / serialization issues — silent
  }
}

export function getChatHistory(): ChatSession[] {
  return safeRead<ChatSession[]>(CHAT_HISTORY_KEY, []);
}

export function getChatSession(id: string): ChatSession | null {
  return getChatHistory().find((s) => s.id === id) ?? null;
}

export function saveChatSession(session: ChatSession) {
  const sessions = getChatHistory().filter((s) => s.id !== session.id);
  const next = [session, ...sessions].slice(0, MAX_SESSIONS);
  safeWrite(CHAT_HISTORY_KEY, next);
}

export function deleteChatSession(id: string) {
  const next = getChatHistory().filter((s) => s.id !== id);
  safeWrite(CHAT_HISTORY_KEY, next);
}

export function clearChatHistory() {
  if (!isClient()) return;
  window.localStorage.removeItem(CHAT_HISTORY_KEY);
  window.localStorage.removeItem(ACTIVE_SESSION_KEY);
}

export function getActiveSessionId(): string | null {
  return safeRead<string | null>(ACTIVE_SESSION_KEY, null);
}

export function setActiveSessionId(id: string | null) {
  if (!isClient()) return;
  if (id === null) {
    window.localStorage.removeItem(ACTIVE_SESSION_KEY);
  } else {
    safeWrite(ACTIVE_SESSION_KEY, id);
  }
}

export function createSession(initialMessage?: string): ChatSession {
  const now = new Date().toISOString();
  const id = `chat_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
  const title =
    initialMessage && initialMessage.trim().length > 0
      ? initialMessage.trim().slice(0, 60) + (initialMessage.length > 60 ? "…" : "")
      : "New conversation";

  return {
    id,
    title,
    created_at: now,
    updated_at: now,
    messages: [],
    status: "IDLE",
  };
}

export function appendMessage(
  session: ChatSession,
  message: Omit<ChatMessage, "id" | "timestamp">,
): ChatSession {
  const msg: ChatMessage = {
    ...message,
    id: `msg_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    timestamp: new Date().toISOString(),
  };
  return {
    ...session,
    messages: [...session.messages, msg],
    updated_at: msg.timestamp,
    title:
      session.messages.length === 0 && message.role === "user"
        ? message.content.trim().slice(0, 60) +
          (message.content.length > 60 ? "…" : "")
        : session.title,
  };
}