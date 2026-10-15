"use client";

import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Orbit,
  Plus,
  ArrowUp,
  BrainCircuit,
  FileUp,
  X,
  Search,
  History as HistoryIcon,
  Sparkles,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Trash2,
  LoaderCircle,
  Menu,
  FileText,
} from "lucide-react";

type ResearchMode = "standard" | "deep";

type ResearchSource = {
  title: string;
  url: string;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode?: ResearchMode;
  sources?: ResearchSource[];
  isLoading?: boolean;
};

type Conversation = {
  id: string;
  title: string;
  updatedAt: number;
  messages: ChatMessage[];
  documentId?: number;
  backendConversationId?: number;
};

const HISTORY_KEY = "scout_research_history_v1";

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:3001/api"
).replace(/\/+$/, "");

function createId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function getRecord(
  value: unknown
): Record<string, unknown> | undefined {
  if (
    value &&
    typeof value === "object" &&
    !Array.isArray(value)
  ) {
    return value as Record<string, unknown>;
  }

  return undefined;
}

function getPayload(value: unknown): unknown {
  const record = getRecord(value);

  if (record?.data !== undefined) return record.data;
  if (record?.result !== undefined) return record.result;

  return value;
}

function toText(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  return value.filter(
    (item): item is string => typeof item === "string"
  );
}

function toSourceLinks(value: unknown): string {
  return toStringArray(value)
    .map((source) => {
      const text = source.trim();

      // Preserve links already formatted as Markdown.
      if (/^\[.+\]\(https?:\/\/[^)]+\)$/.test(text)) {
        return `- ${text}`;
      }

      try {
        const url = new URL(text);

        if (!["http:", "https:"].includes(url.protocol)) {
          return "";
        }

        return `- [${url.hostname}](${url.href})`;
      } catch {
        return `- ${text}`;
      }
    })
    .filter(Boolean)
    .join("\n");
}

function formatDeepResearchResult(
  report: Record<string, unknown>
): string {
  const lines: string[] = [
    "# Deep Research Report",
    "",
    "## Executive Summary",
    "",
    toText(report.research_overview) ||
      "No research overview was provided.",
    "",
  ];

  // Verification overview
  const summary = getRecord(report.verification_summary);

  if (summary) {
    const verdicts = getRecord(summary.verdict_counts);

    lines.push("## Evidence Verification Summary", "");

    lines.push(
      `- **Claims checked:** ${summary.claims_checked ?? "N/A"}`,
      `- **Sources extracted:** ${summary.extracted_source_count ?? "N/A"}`,
      `- **Sources requested:** ${summary.requested_source_count ?? "N/A"}`,
      `- **Failed claims:** ${summary.failed_claim_count ?? "N/A"}`
    );

    if (verdicts) {
      lines.push(
        "",
        "| Verification status | Count |",
        "|---|---:|"
      );

      for (const [status, count] of Object.entries(verdicts)) {
        lines.push(
          `| ${status.replace(/_/g, " ")} | ${String(count)} |`
        );
      }
    }

    lines.push("");
  }

  // Main findings
  if (Array.isArray(report.key_findings)) {
    lines.push("## Key Findings", "");

    report.key_findings.forEach((item, index) => {
      const finding = getRecord(item);

      if (!finding) return;

      const verification = getRecord(finding.verification);

      lines.push(
        `### ${index + 1}. ${toText(finding.finding) || "Finding"}`,
        ""
      );

      if (finding.confidence) {
        lines.push(`**Confidence:** ${String(finding.confidence)}`, "");
      }

      if (verification?.verdict) {
        lines.push(
          `**Evidence status:** ${String(verification.verdict).replace(/_/g, " ")}`,
          ""
        );
      }

      if (verification?.reasoning) {
        lines.push(
          "**Assessment**",
          "",
          toText(verification.reasoning),
          ""
        );
      }

      const supported = toStringArray(
        verification?.supported_aspects
      );

      if (supported.length > 0) {
        lines.push("**Supported aspects**", "");

        supported.forEach((aspect) => {
          lines.push(`- ${aspect}`);
        });

        lines.push("");
      }

      const unsupported = toStringArray(
        verification?.unsupported_aspects
      );

      if (unsupported.length > 0) {
        lines.push("**Unsupported or unverified aspects**", "");

        unsupported.forEach((aspect) => {
          lines.push(`- ${aspect}`);
        });

        lines.push("");
      }

      const links = toSourceLinks(finding.source_urls);

      if (links) {
        lines.push("**Sources**", "", links, "");
      }

      const checks = toStringArray(
        verification?.additional_checks
      );

      if (checks.length > 0 && checks[0] !== "None") {
        lines.push("**Further verification needed**", "");

        checks.forEach((check) => {
          lines.push(`- ${check}`);
        });

        lines.push("");
      }
    });
  }

  // Approach comparisons
  if (Array.isArray(report.comparisons)) {
    lines.push("## Comparisons", "");

    report.comparisons.forEach((item) => {
      const comparison = getRecord(item);

      if (!comparison) return;

      lines.push(
        `### ${toText(comparison.dimension) || "Comparison"}`,
        "",
        toText(comparison.observation),
        ""
      );

      const verification = getRecord(comparison.verification);

      if (verification?.verdict) {
        lines.push(
          `**Evidence status:** ${String(verification.verdict).replace(/_/g, " ")}`,
          ""
        );
      }

      if (verification?.reasoning) {
        lines.push(toText(verification.reasoning), "");
      }

      const links = toSourceLinks(comparison.source_urls);

      if (links) {
        lines.push("**Sources**", "", links, "");
      }

      const checks = toStringArray(
        verification?.additional_checks
      );

      if (checks.length > 0) {
        lines.push("**Next verification steps**", "");

        checks.forEach((check) => {
          lines.push(`- ${check}`);
        });

        lines.push("");
      }
    });
  }

  // Contradictions or unresolved claims
  if (Array.isArray(report.contradictions)) {
    lines.push("## Conflicting or Unresolved Claims", "");

    report.contradictions.forEach((item) => {
      const contradiction = getRecord(item);

      if (!contradiction) return;

      lines.push(
        `### ${toText(contradiction.topic) || "Claim under review"}`,
        ""
      );

      const claims = toStringArray(contradiction.claims);

      claims.forEach((claim) => {
        lines.push(`- ${claim}`);
      });

      if (claims.length > 0) lines.push("");

      if (contradiction.what_needs_verification) {
        lines.push(
          "**What still needs verification**",
          "",
          toText(contradiction.what_needs_verification),
          ""
        );
      }
    });
  }

  // Research gaps
  if (Array.isArray(report.candidate_research_gaps)) {
    lines.push("## Candidate Research Gaps", "");

    report.candidate_research_gaps.forEach((item, index) => {
      const gap = getRecord(item);

      if (!gap) return;

      lines.push(
        `### ${index + 1}. ${toText(gap.gap) || "Research gap"}`,
        ""
      );

      if (gap.confidence) {
        lines.push(`**Confidence:** ${String(gap.confidence)}`, "");
      }

      if (gap.reasoning) {
        lines.push("**Why it matters**", "", toText(gap.reasoning), "");
      }

      if (gap.validation_needed) {
        lines.push(
          "**How to investigate it**",
          "",
          toText(gap.validation_needed),
          ""
        );
      }

      const links = toSourceLinks(gap.source_urls);

      if (links) {
        lines.push("**Related sources**", "", links, "");
      }
    });
  }

  if (report.verification_scope_note) {
    lines.push(
      "## Evidence Limitations",
      "",
      toText(report.verification_scope_note),
      ""
    );
  }

  return lines.join("\n").trim();
}

function tryParseJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return undefined;
  }
}

function isDeepReport(
  record: Record<string, unknown> | undefined | null
): record is Record<string, unknown> {
  return Boolean(
    record &&
      typeof record.research_overview === "string" &&
      Array.isArray(record.key_findings)
  );
}

function getAnswer(value: unknown): string {
  let root = getPayload(value);

  // Case 1: The entire response is a JSON string.
  if (typeof root === "string") {
    const trimmed = root.trim();

    // Only try to parse strings that look like JSON objects/arrays.
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      const parsed = tryParseJson(trimmed);

      if (parsed === undefined) {
        return root;
      }

      root = parsed;
    } else {
      return root;
    }
  }

  const record = getRecord(root);

  if (!record) {
    return typeof root === "string"
      ? root
      : JSON.stringify(root, null, 2);
  }

  // Case 2: The response itself contains the research report.
  if (isDeepReport(record)) {
    return formatDeepResearchResult(record);
  }

  // Case 3: The report is stored inside a text/object field.
  for (const key of [
    "answer",
    "response",
    "report",
    "summary",
    "output",
    "content",
    "text",
  ]) {
    const candidate = record[key];

    if (typeof candidate === "string") {
      const trimmed = candidate.trim();

      if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        const parsed = tryParseJson(trimmed);
        const parsedRecord = getRecord(parsed);

        if (isDeepReport(parsedRecord)) {
          return formatDeepResearchResult(parsedRecord);
        }
      }

      return candidate;
    }

    if (candidate && typeof candidate === "object") {
      const candidateRecord = getRecord(candidate);

      if (isDeepReport(candidateRecord)) {
        return formatDeepResearchResult(candidateRecord);
      }

      return JSON.stringify(candidate, null, 2);
    }
  }

  return JSON.stringify(root, null, 2);
}

function getSources(value: unknown): ResearchSource[] {
  const outer = getRecord(value);
  const root = getRecord(getPayload(value));
  const candidates = root?.sources ?? outer?.sources;

  if (!Array.isArray(candidates)) return [];

  return candidates
    .map((item): ResearchSource | null => {
      if (typeof item === "string") {
        try {
          const url = new URL(item);

          if (!["http:", "https:"].includes(url.protocol)) {
            return null;
          }

          return {
            title: url.hostname,
            url: url.href,
          };
        } catch {
          return null;
        }
      }

      const source = getRecord(item);

      if (!source) return null;

      const rawUrl =
        source.url ??
        source.link ??
        source.href ??
        source.source_url;

      if (typeof rawUrl !== "string") return null;

      try {
        const url = new URL(rawUrl);

        if (!["http:", "https:"].includes(url.protocol)) {
          return null;
        }

        const title =
          source.title ??
          source.name ??
          source.label ??
          url.hostname;

        return {
          title: typeof title === "string" ? title : url.hostname,
          url: url.href,
        };
      } catch {
        return null;
      }
    })
    .filter(
      (source): source is ResearchSource => source !== null
    );
}

/**
 * Normalize common formatting inconsistencies returned by LLMs.
 * Markdown tables and other GitHub Flavored Markdown are rendered
 * by ReactMarkdown and remark-gfm below.
 */
function normalizeMarkdown(content: string) {
  return content
    .replace(/\r\n?/g, "\n")
    .replace(/<br\s*\/?>/gi, " · ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function getHistoryGroup(timestamp: number) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const date = new Date(timestamp);
  date.setHours(0, 0, 0, 0);

  const daysAgo = Math.floor(
    (today.getTime() - date.getTime()) / 86_400_000
  );

  if (daysAgo <= 0) return "Today";
  if (daysAgo === 1) return "Yesterday";
  if (daysAgo < 7) return "Previous 7 days";

  return "Older";
}

export default function ResearchPage() {
  const router = useRouter();

  const [authenticated, setAuthenticated] = useState(false);
  const [historyReady, setHistoryReady] = useState(false);

  const [conversations, setConversations] = useState<
    Conversation[]
  >([]);

  const [activeConversationId, setActiveConversationId] =
    useState<string | null>(null);

  const [openHistoryMenuId, setOpenHistoryMenuId] = useState<
    string | null
  >(null);

  const [input, setInput] = useState("");
  const [mode, setMode] = useState<ResearchMode>("standard");
  const [isSending, setIsSending] = useState(false);

  const [searchHistory, setSearchHistory] = useState("");
  const [mobileHistoryOpen, setMobileHistoryOpen] =
    useState(false);
  const [attachmentMenuOpen, setAttachmentMenuOpen] =
    useState(false);
  const [selectedPdf, setSelectedPdf] = useState<File | null>(
    null
  );
  const [composerNotice, setComposerNotice] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Authentication check.
  useEffect(() => {
    const token = window.sessionStorage.getItem("scout_token");

    if (!token) {
      router.replace("/login");
      return;
    }

    setAuthenticated(true);
  }, [router]);

  // Load local conversation history.
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(HISTORY_KEY);

      if (saved) {
        const parsed: unknown = JSON.parse(saved);

        if (Array.isArray(parsed)) {
          setConversations(parsed as Conversation[]);
        }
      }
    } catch (error) {
      console.error("Could not load Scout history:", error);
    } finally {
      setHistoryReady(true);
    }
  }, []);

  // Save conversation history in this browser.
  useEffect(() => {
    if (!historyReady) return;

    try {
      window.localStorage.setItem(
        HISTORY_KEY,
        JSON.stringify(conversations)
      );
    } catch (error) {
      console.error("Could not save Scout history:", error);
    }
  }, [conversations, historyReady]);

  // Close the history options menu when clicking elsewhere.
  useEffect(() => {
    if (!openHistoryMenuId) return;

    function handleOutsideClick(event: MouseEvent) {
      const target = event.target as HTMLElement | null;

      if (!target?.closest("[data-history-menu]")) {
        setOpenHistoryMenuId(null);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);

    return () =>
      document.removeEventListener(
        "mousedown",
        handleOutsideClick
      );
  }, [openHistoryMenuId]);

  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeConversationId
  );

  const activeMessages = activeConversation?.messages ?? [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [activeMessages]);

  function startNewResearch() {
    setActiveConversationId(null);
    setInput("");
    setMode("standard");
    setSelectedPdf(null);
    setComposerNotice("");
    setAttachmentMenuOpen(false);
    setMobileHistoryOpen(false);
    setOpenHistoryMenuId(null);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function renameConversation(conversationId: string) {
    const conversation = conversations.find(
      (item) => item.id === conversationId
    );

    if (!conversation) return;

    const newTitle = window.prompt(
      "Rename research",
      conversation.title || "New research"
    );

    setOpenHistoryMenuId(null);

    if (newTitle === null) return;

    const trimmedTitle = newTitle.trim();

    if (!trimmedTitle) return;

    setConversations((previous) =>
      previous.map((item) =>
        item.id === conversationId
          ? {
              ...item,
              title: trimmedTitle,
              updatedAt: Date.now(),
            }
          : item
      )
    );
  }

  function deleteConversation(conversationId: string) {
    const conversation = conversations.find(
      (item) => item.id === conversationId
    );

    if (!conversation) return;

    const confirmed = window.confirm(
      `Delete "${conversation.title || "New research"}"?`
    );

    setOpenHistoryMenuId(null);

    if (!confirmed) return;

    setConversations((previous) =>
      previous.filter((item) => item.id !== conversationId)
    );

    if (activeConversationId === conversationId) {
      startNewResearch();
    }
  }

  function updateAssistantMessage(
    conversationId: string,
    messageId: string,
    changes: Partial<ChatMessage>
  ) {
    setConversations((previous) =>
      previous.map((conversation) => {
        if (conversation.id !== conversationId) {
          return conversation;
        }

        return {
          ...conversation,
          updatedAt: Date.now(),
          messages: conversation.messages.map((message) =>
            message.id === messageId
              ? { ...message, ...changes }
              : message
          ),
        };
      })
    );
  }

  async function handleSend() {
    const prompt = input.trim();
    const pdfToUpload = selectedPdf;

    if (!prompt || isSending) return;

    const token = window.sessionStorage.getItem("scout_token");

    if (!token) {
      router.replace("/login");
      return;
    }

    const existingConversation = conversations.find(
      (conversation) => conversation.id === activeConversationId
    );

    const isPdfResearch = Boolean(
      pdfToUpload || existingConversation?.backendConversationId
    );

    const effectiveMode: ResearchMode = isPdfResearch
      ? "standard"
      : mode;

    if (isPdfResearch && mode === "deep") {
      setMode("standard");
    }

    // A newly attached PDF starts a separate conversation
    // when the active conversation already has messages.
    let conversationId: string;

    if (
      !activeConversationId ||
      (pdfToUpload && activeMessages.length > 0)
    ) {
      conversationId = createId();
    } else {
      conversationId = activeConversationId;
    }

    let backendConversationId: number | undefined = pdfToUpload
      ? undefined
      : existingConversation?.backendConversationId;

    const userMessage: ChatMessage = {
      id: createId(),
      role: "user",
      content: prompt,
      mode: effectiveMode,
    };

    const assistantMessage: ChatMessage = {
      id: createId(),
      role: "assistant",
      content: "",
      mode: effectiveMode,
      isLoading: true,
    };

    setConversations((previous) => {
      const existing = previous.find(
        (conversation) => conversation.id === conversationId
      );

      if (existing) {
        return [
          {
            ...existing,
            title:
              existing.messages.length === 0
                ? prompt.slice(0, 48)
                : existing.title,
            updatedAt: Date.now(),
            messages: [
              ...existing.messages,
              userMessage,
              assistantMessage,
            ],
          },
          ...previous.filter(
            (conversation) =>
              conversation.id !== conversationId
          ),
        ];
      }

      return [
        {
          id: conversationId,
          title: prompt.slice(0, 48),
          updatedAt: Date.now(),
          messages: [userMessage, assistantMessage],
        },
        ...previous,
      ];
    });

    setActiveConversationId(conversationId);
    setInput("");
    setComposerNotice("");
    setAttachmentMenuOpen(false);
    setIsSending(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      // 1. Upload and index the selected PDF.
      if (pdfToUpload) {
        const uploadForm = new FormData();
        uploadForm.append("file", pdfToUpload);

        const uploadResponse = await fetch(
          `${API_BASE}/research/documents`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
            },
            body: uploadForm,
          }
        );

        const uploadResult = (await uploadResponse
          .json()
          .catch(() => ({}))) as Record<string, unknown>;

        if (!uploadResponse.ok) {
          throw new Error(
            typeof uploadResult.error === "string"
              ? uploadResult.error
              : "PDF upload failed."
          );
        }

        const documentId = Number(uploadResult.document_id);

        if (!Number.isInteger(documentId) || documentId <= 0) {
          throw new Error(
            "The server did not return a valid document ID."
          );
        }

        // 2. Create a conversation linked to the PDF.
        const conversationResponse = await fetch(
          `${API_BASE}/research/conversations`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              document_id: documentId,
            }),
          }
        );

        const conversationResult = (await conversationResponse
          .json()
          .catch(() => ({}))) as Record<string, unknown>;

        if (!conversationResponse.ok) {
          throw new Error(
            typeof conversationResult.error === "string"
              ? conversationResult.error
              : "Could not create a PDF conversation."
          );
        }

        const newBackendConversationId = Number(
          conversationResult.conversation_id
        );

        if (
          !Number.isInteger(newBackendConversationId) ||
          newBackendConversationId <= 0
        ) {
          throw new Error(
            "The server did not return a valid conversation ID."
          );
        }

        backendConversationId = newBackendConversationId;

        // Persist the IDs for this browser conversation.
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === conversationId
              ? {
                  ...conversation,
                  documentId,
                  backendConversationId: newBackendConversationId,
                }
              : conversation
          )
        );

        setSelectedPdf(null);
        setComposerNotice(
          `PDF "${pdfToUpload.name}" uploaded and indexed successfully.`
        );
      }

      // 3. Route the query to the selected research service.
      const endpoint = backendConversationId
        ? `${API_BASE}/research/chat`
        : effectiveMode === "deep"
          ? `${API_BASE}/research/advanced`
          : `${API_BASE}/research`;

      const requestBody = backendConversationId
        ? {
            conversation_id: backendConversationId,
            query: prompt,
          }
        : { query: prompt };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(requestBody),
      });

      const result: unknown = await response
        .json()
        .catch(() => ({}));

      const record = getRecord(result);

      if (!response.ok || record?.success === false) {
        const errorMessage =
          typeof record?.error === "string"
            ? record.error
            : typeof record?.detail === "string"
              ? record.detail
              : `Research request failed (${response.status}).`;

        throw new Error(errorMessage);
      }

      const answer = getAnswer(result);
      const sources = getSources(result);

      updateAssistantMessage(conversationId, assistantMessage.id, {
        content:
          answer ||
          "Scout received a response but returned no text.",
        sources,
        isLoading: false,
      });
    } catch (error) {
      console.error("Scout research failed:", error);

      updateAssistantMessage(conversationId, assistantMessage.id, {
        content:
          error instanceof Error
            ? `I couldn't complete this research request: ${error.message}`
            : "I couldn't complete this research request. Please try again.",
        isLoading: false,
      });
    } finally {
      setIsSending(false);
    }
  }

  function handleTextareaChange(
    event: ChangeEvent<HTMLTextAreaElement>
  ) {
    setInput(event.target.value);
    setComposerNotice("");

    event.target.style.height = "auto";
    event.target.style.height = `${Math.min(
      event.target.scrollHeight,
      192
    )}px`;
  }

  function handleComposerKeyDown(
    event: KeyboardEvent<HTMLTextAreaElement>
  ) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  }

  function handlePdfSelection(
    event: ChangeEvent<HTMLInputElement>
  ) {
    const file = event.target.files?.[0];

    if (!file) return;

    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      setComposerNotice("Please select a PDF file.");
      event.target.value = "";
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setComposerNotice(
        "This PDF is larger than the 25 MB upload limit."
      );
      event.target.value = "";
      return;
    }

    setSelectedPdf(file);
    setComposerNotice(
      "PDF selected. Enter a question and send it to upload and index your document."
    );
    setAttachmentMenuOpen(false);
    event.target.value = "";
  }

  const orderedConversations = [...conversations].sort(
    (a, b) => b.updatedAt - a.updatedAt
  );

  const historyGroups = [
    "Today",
    "Yesterday",
    "Previous 7 days",
    "Older",
  ];

  const matchingConversations = orderedConversations.filter(
    (conversation) =>
      (conversation.title || "")
        .toLowerCase()
        .includes(searchHistory.toLowerCase())
  );

  if (!authenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#05080D] text-white">
        <div className="flex items-center gap-3 text-sm text-white/60">
          <LoaderCircle className="h-4 w-4 animate-spin" />
          Opening Scout...
        </div>
      </main>
    );
  }

  return (
    <div className="relative h-dvh overflow-hidden bg-[#05080D] text-[#F4F7FB]">
      {mobileHistoryOpen && (
        <button
          type="button"
          aria-label="Close chat history"
          onClick={() => setMobileHistoryOpen(false)}
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
        />
      )}

      <div className="relative z-10 flex h-full min-h-0">
        {/* Left chat history sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-40 flex w-[280px] shrink-0 flex-col border-r border-white/[0.09] bg-[#070C12]/95 backdrop-blur-2xl transition-transform duration-300 lg:static lg:z-20 lg:translate-x-0 ${
            mobileHistoryOpen
              ? "translate-x-0"
              : "-translate-x-full"
          }`}
        >
          <div className="flex h-[76px] shrink-0 items-center justify-between border-b border-white/[0.07] px-5">
            <Link href="/" className="flex items-center gap-2.5">
              <Orbit
                className="h-6 w-6 text-cyan-300"
                strokeWidth={1.6}
              />

              <span className="font-[family-name:var(--font-scout-wordmark)] text-xl font-bold tracking-[-0.075em]">
                S C O U T
              </span>
            </Link>

            <button
              type="button"
              onClick={() => setMobileHistoryOpen(false)}
              aria-label="Close history sidebar"
              className="rounded-lg p-2 text-white/45 transition hover:bg-white/[0.06] hover:text-white lg:hidden"
            >
              <X size={17} />
            </button>
          </div>

          <div className="space-y-3 px-3 py-4">
            <button
              type="button"
              onClick={startNewResearch}
              className="flex w-full items-center gap-3 rounded-xl border border-cyan-300/20 bg-cyan-300/[0.07] px-3.5 py-3 text-sm font-medium text-white transition hover:border-cyan-300/40 hover:bg-cyan-300/[0.11]"
            >
              <Plus size={17} className="text-cyan-300" />
              New research
            </button>

            <label className="flex items-center gap-2.5 rounded-xl border border-white/[0.09] bg-white/[0.025] px-3.5 transition focus-within:border-cyan-300/35">
              <Search size={16} className="shrink-0 text-white/35" />

              <input
                type="search"
                value={searchHistory}
                onChange={(event) =>
                  setSearchHistory(event.target.value)
                }
                placeholder="Search history"
                className="min-w-0 flex-1 bg-transparent py-2.5 text-xs text-white outline-none placeholder:text-white/35"
              />
            </label>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-5">
            <div className="mb-4 flex items-center gap-2 px-2 pt-2 text-[10px] font-medium tracking-[0.19em] text-white/35">
              <HistoryIcon size={13} />
              RECENT RESEARCH
            </div>

            {!historyReady ? (
              <div className="px-3 py-4 text-xs text-white/40">
                Loading history...
              </div>
            ) : matchingConversations.length === 0 ? (
              <div className="px-3 py-5">
                <MessageSquare className="mb-3 h-5 w-5 text-white/25" />

                <p className="text-sm text-white/55">
                  {searchHistory
                    ? "No matching research found."
                    : "Your conversations will appear here."}
                </p>

                <p className="mt-1 text-xs leading-5 text-white/30">
                  Start a new research session to build your history.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {historyGroups.map((group) => {
                  const items = matchingConversations.filter(
                    (conversation) =>
                      getHistoryGroup(conversation.updatedAt) === group
                  );

                  if (items.length === 0) return null;

                  return (
                    <section key={group}>
                      <p className="mb-2 px-2 text-[10px] font-medium tracking-[0.14em] text-white/35">
                        {group.toUpperCase()}
                      </p>

                      <div className="space-y-1">
                        {items.map((conversation) => {
                          const active =
                            conversation.id === activeConversationId;
                          const menuOpen =
                            openHistoryMenuId === conversation.id;

                          return (
                            <div
                              key={conversation.id}
                              data-history-menu
                              className="group relative"
                            >
                              <div
                                className={`flex w-full items-center gap-1 rounded-lg px-3 py-2.5 text-sm transition ${
                                  active
                                    ? "border border-white/[0.08] bg-white/[0.07] text-white"
                                    : "border border-transparent text-white/60 hover:bg-white/[0.045] hover:text-white/90"
                                }`}
                              >
                                {/* Select conversation */}
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActiveConversationId(
                                      conversation.id
                                    );
                                    setMobileHistoryOpen(false);
                                    setOpenHistoryMenuId(null);
                                  }}
                                  className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
                                >
                                  <MessageSquare
                                    size={15}
                                    className={`shrink-0 ${
                                      active
                                        ? "text-cyan-300"
                                        : "text-white/30"
                                    }`}
                                  />

                                  <span className="min-w-0 flex-1 truncate">
                                    {conversation.title ||
                                      "New research"}
                                  </span>
                                </button>

                                {/* Three-dot menu */}
                                <button
                                  type="button"
                                  aria-label="Conversation options"
                                  aria-expanded={menuOpen}
                                  onClick={() =>
                                    setOpenHistoryMenuId((current) =>
                                      current === conversation.id
                                        ? null
                                        : conversation.id
                                    )
                                  }
                                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition hover:bg-white/[0.08] hover:text-white ${
                                    menuOpen
                                      ? "bg-white/[0.08] text-white"
                                      : "text-white/50 opacity-100 sm:opacity-0 sm:focus:opacity-100 sm:group-hover:opacity-100"
                                  }`}
                                >
                                  <MoreHorizontal size={17} />
                                </button>
                              </div>

                              {/* Options menu */}
                              {menuOpen && (
                                <div className="absolute right-1 top-full z-50 mt-1 w-36 rounded-lg border border-white/10 bg-[#11151D] p-1 shadow-xl">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      renameConversation(
                                        conversation.id
                                      )
                                    }
                                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-white/80 transition hover:bg-white/[0.07] hover:text-white"
                                  >
                                    <Pencil size={14} />
                                    Rename
                                  </button>

                                  <button
                                    type="button"
                                    onClick={() =>
                                      deleteConversation(
                                        conversation.id
                                      )
                                    }
                                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-red-400 transition hover:bg-red-500/10"
                                  >
                                    <Trash2 size={14} />
                                    Delete
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </section>
                  );
                })}
              </div>
            )}
          </div>

          <div className="shrink-0 border-t border-white/[0.07] p-4">
            <div className="flex items-center gap-3 rounded-xl px-2 py-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-full border border-cyan-300/20 bg-cyan-300/[0.08]">
                <Sparkles size={16} className="text-cyan-300" />
              </div>

              <div className="min-w-0">
                <p className="text-sm font-medium text-white/85">
                  Scout Research
                </p>
                <p className="mt-0.5 text-[11px] text-white/40">
                  Your research space
                </p>
              </div>
            </div>
          </div>
        </aside>

        {/* Main research workspace */}
        <main className="flex min-h-0 min-w-0 flex-1 flex-col">
          <header className="flex h-[76px] shrink-0 items-center justify-between border-b border-white/[0.07] px-4 sm:px-7">
            <div className="flex min-w-0 items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileHistoryOpen(true)}
                aria-label="Open chat history"
                className="rounded-lg border border-white/[0.09] bg-white/[0.025] p-2.5 text-white/60 transition hover:bg-white/[0.07] hover:text-white lg:hidden"
              >
                <Menu size={18} />
              </button>

              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-white/85">
                  {activeConversation?.title || "New research"}
                </p>

                <p className="mt-1 text-[11px] text-white/40">
                  {mode === "deep"
                    ? "Deep research mode"
                    : "Research workspace"}
                </p>
              </div>
            </div>

            <div
              className={`hidden items-center gap-2 rounded-full border px-3 py-1.5 sm:flex ${
                mode === "deep"
                  ? "border-cyan-300/30 bg-cyan-300/[0.07] text-cyan-200"
                  : "border-white/[0.09] bg-white/[0.025] text-white/50"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  mode === "deep" ? "bg-cyan-300" : "bg-white/30"
                }`}
              />

              <span className="text-[11px]">
                {mode === "deep"
                  ? "Deep Research"
                  : "Standard Research"}
              </span>
            </div>
          </header>

          {/* Conversation / welcome screen */}
          <div className="min-h-0 flex-1 overflow-y-auto">
            {activeMessages.length === 0 ? (
              <div className="flex min-h-full flex-col items-center justify-center px-5 py-10">
                <div className="mb-6 flex h-[60px] w-[60px] items-center justify-center rounded-2xl border border-cyan-300/20 bg-cyan-300/[0.055] shadow-[0_0_45px_rgba(34,211,238,0.055)]">
                  <Orbit
                    className="h-8 w-8 text-cyan-300"
                    strokeWidth={1.5}
                  />
                </div>

                <p className="mb-3 text-[10px] font-medium tracking-[0.24em] text-cyan-300/80">
                  YOUR RESEARCH, CONTINUED
                </p>

                <h1 className="max-w-2xl text-center text-3xl font-medium leading-tight tracking-[-0.05em] sm:text-4xl lg:text-5xl">
                  What do you want to{" "}
                  <span className="font-serif font-normal italic text-cyan-300">
                    discover?
                  </span>
                </h1>

                <p className="mt-5 max-w-lg text-center text-sm leading-7 text-white/50 sm:text-base">
                  Ask a question, explore a topic, or investigate a
                  complex problem. Scout helps you turn curiosity into
                  source-backed research.
                </p>

                <div className="mt-10 grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-3">
                  {[
                    {
                      title: "Understand a topic",
                      description:
                        "Break down a complex idea into clear concepts.",
                      prompt:
                        "Explain a complex topic clearly, with examples and reliable sources.",
                    },
                    {
                      title: "Compare technologies",
                      description:
                        "Explore the trade-offs between two approaches.",
                      prompt:
                        "Compare two technologies, including their strengths, limitations, and use cases.",
                    },
                    {
                      title: "Explore the evidence",
                      description:
                        "Find sources and investigate a question.",
                      prompt:
                        "Research a topic using reliable sources and summarize the most important findings.",
                    },
                  ].map((suggestion) => (
                    <button
                      key={suggestion.title}
                      type="button"
                      onClick={() => {
                        setInput(suggestion.prompt);
                        textareaRef.current?.focus();
                      }}
                      className="group rounded-xl border border-white/[0.09] bg-white/[0.018] p-4 text-left transition duration-300 hover:-translate-y-0.5 hover:border-cyan-300/25 hover:bg-cyan-300/[0.035]"
                    >
                      <p className="text-sm font-medium text-white/80 transition group-hover:text-cyan-100">
                        {suggestion.title}
                      </p>

                      <p className="mt-2 text-xs leading-5 text-white/40">
                        {suggestion.description}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-7 sm:py-10">
                <div className="space-y-8">
                  {activeMessages.map((message) => (
                    <article
                      key={message.id}
                      className={
                        message.role === "user"
                          ? "flex justify-end"
                          : "flex items-start gap-3 sm:gap-4"
                      }
                    >
                      {message.role === "assistant" && (
                        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-cyan-300/20 bg-cyan-300/[0.06]">
                          <Orbit
                            className="h-4 w-4 text-cyan-300"
                            strokeWidth={1.5}
                          />
                        </div>
                      )}

                      <div
                        className={
                          message.role === "user"
                            ? "max-w-[88%] rounded-2xl border border-white/[0.09] bg-white/[0.045] px-4 py-3 text-sm leading-7 text-white/85 sm:max-w-[78%] sm:px-5"
                            : "min-w-0 flex-1 pt-1"
                        }
                      >
                        {message.role === "assistant" && (
                          <div className="mb-3 flex items-center gap-2">
                            <span className="text-sm font-medium text-white/85">
                              Scout
                            </span>

                            {message.mode === "deep" && (
                              <span className="rounded-full border border-cyan-300/20 bg-cyan-300/[0.06] px-2 py-0.5 text-[10px] text-cyan-200">
                                Deep Research
                              </span>
                            )}
                          </div>
                        )}

                        {message.isLoading ? (
                          <div className="flex items-center gap-3 py-2 text-sm text-white/50">
                            <LoaderCircle className="h-4 w-4 animate-spin text-cyan-300" />

                            {message.mode === "deep"
                              ? "Scout is conducting a multi-step investigation..."
                              : "Scout is researching your question..."}
                          </div>
                        ) : message.role === "assistant" ? (
                          <div className="break-words text-sm leading-7 text-white/80">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                h1: ({ children }) => (
                                  <h1 className="mb-4 mt-7 text-2xl font-semibold leading-tight tracking-tight text-white first:mt-0">
                                    {children}
                                  </h1>
                                ),
                                h2: ({ children }) => (
                                  <h2 className="mb-3 mt-7 text-xl font-semibold leading-tight tracking-tight text-white">
                                    {children}
                                  </h2>
                                ),
                                h3: ({ children }) => (
                                  <h3 className="mb-2 mt-5 text-base font-semibold text-white/95">
                                    {children}
                                  </h3>
                                ),
                                p: ({ children }) => (
                                  <p className="my-3 leading-7 text-white/75">
                                    {children}
                                  </p>
                                ),
                                strong: ({ children }) => (
                                  <strong className="font-semibold text-white">
                                    {children}
                                  </strong>
                                ),
                                em: ({ children }) => (
                                  <em className="text-cyan-100/90">
                                    {children}
                                  </em>
                                ),
                                ul: ({ children }) => (
                                  <ul className="my-4 list-disc space-y-2 pl-6 text-white/75 marker:text-cyan-300">
                                    {children}
                                  </ul>
                                ),
                                ol: ({ children }) => (
                                  <ol className="my-4 list-decimal space-y-2 pl-6 text-white/75 marker:text-cyan-300">
                                    {children}
                                  </ol>
                                ),
                                li: ({ children }) => (
                                  <li className="pl-1 leading-7">
                                    {children}
                                  </li>
                                ),
                                blockquote: ({ children }) => (
                                  <blockquote className="my-4 border-l-2 border-cyan-300/50 pl-4 text-white/60">
                                    {children}
                                  </blockquote>
                                ),
                                a: ({ href, children }) => (
                                  <a
                                    href={href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-cyan-300 underline decoration-cyan-300/30 underline-offset-4 transition hover:text-cyan-200"
                                  >
                                    {children}
                                  </a>
                                ),
                                table: ({ children }) => (
                                  <div className="my-5 w-full overflow-x-auto rounded-xl border border-white/10">
                                    <table className="w-full border-collapse text-left text-sm">
                                      {children}
                                    </table>
                                  </div>
                                ),
                                thead: ({ children }) => (
                                  <thead className="bg-white/[0.05] text-white">
                                    {children}
                                  </thead>
                                ),
                                tbody: ({ children }) => (
                                  <tbody className="divide-y divide-white/[0.06]">
                                    {children}
                                  </tbody>
                                ),
                                tr: ({ children }) => (
                                  <tr className="transition hover:bg-white/[0.025]">
                                    {children}
                                  </tr>
                                ),
                                th: ({ children }) => (
                                  <th className="border-b border-white/10 px-4 py-3 font-semibold">
                                    {children}
                                  </th>
                                ),
                                td: ({ children }) => (
                                  <td className="border-b border-white/[0.06] px-4 py-3 align-top text-white/70">
                                    {children}
                                  </td>
                                ),
                                hr: () => (
                                  <hr className="my-6 border-white/10" />
                                ),
                                pre: ({ children }) => (
                                  <pre className="my-4 overflow-x-auto rounded-xl border border-white/10 bg-[#080D14] p-4 text-xs leading-6 text-cyan-50">
                                    {children}
                                  </pre>
                                ),
                                code: ({ children, className }) => {
                                  const isBlockCode =
                                    Boolean(className) ||
                                    String(children).includes("\n");

                                  return isBlockCode ? (
                                    <code className="font-mono text-xs text-cyan-50">
                                      {children}
                                    </code>
                                  ) : (
                                    <code className="rounded-md border border-white/[0.06] bg-white/[0.06] px-1.5 py-0.5 font-mono text-[0.88em] text-cyan-100">
                                      {children}
                                    </code>
                                  );
                                },
                              }}
                            >
                              {normalizeMarkdown(
                                getAnswer(message.content)
                              )}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <div className="whitespace-pre-wrap break-words">
                            {message.content}
                          </div>
                        )}

                        {!message.isLoading &&
                          message.sources &&
                          message.sources.length > 0 && (
                            <div className="mt-5">
                              <p className="mb-2 text-[10px] font-medium tracking-[0.16em] text-white/40">
                                SOURCES
                              </p>

                              <div className="flex flex-wrap gap-2">
                                {message.sources.map(
                                  (source, index) => (
                                    <a
                                      key={`${source.url}-${index}`}
                                      href={source.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex max-w-full items-center gap-2 rounded-lg border border-white/[0.09] bg-white/[0.025] px-3 py-2 text-xs text-cyan-100/80 transition hover:border-cyan-300/30 hover:bg-cyan-300/[0.045]"
                                    >
                                      <span className="max-w-[220px] truncate">
                                        {index + 1}. {source.title}
                                      </span>
                                    </a>
                                  )
                                )}
                              </div>
                            </div>
                          )}
                      </div>
                    </article>
                  ))}
                </div>

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Composer */}
          <div className="shrink-0 px-3 pb-3 pt-4 sm:px-6 sm:pb-5">
            <div className="mx-auto w-full max-w-4xl">
              <div className="relative rounded-2xl border border-white/[0.12] bg-[#0B1018]/90 shadow-[0_12px_55px_rgba(0,0,0,0.2)] backdrop-blur-xl transition focus-within:border-white/[0.20]">
                {/* Attachment menu */}
                {attachmentMenuOpen && (
                  <div className="absolute bottom-[calc(100%+10px)] left-3 z-30 w-60 overflow-hidden rounded-xl border border-white/[0.12] bg-[#0B111A] p-1.5 shadow-2xl">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition hover:bg-white/[0.055]"
                    >
                      <FileUp size={17} className="text-cyan-300" />

                      <span>
                        <span className="block text-sm text-white/85">
                          Upload PDF
                        </span>

                        <span className="mt-1 block text-[11px] text-white/40">
                          Attach a research document
                        </span>
                      </span>
                    </button>
                  </div>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={handlePdfSelection}
                />

                {/* Selected PDF chip */}
                {selectedPdf && (
                  <div className="px-4 pt-3">
                    <div className="inline-flex max-w-full items-center gap-2 rounded-lg border border-white/[0.1] bg-white/[0.035] px-3 py-2">
                      <FileText
                        size={15}
                        className="shrink-0 text-cyan-300"
                      />

                      <span className="max-w-[220px] truncate text-xs text-white/75">
                        {selectedPdf.name}
                      </span>

                      <button
                        type="button"
                        aria-label="Remove selected PDF"
                        onClick={() => {
                          setSelectedPdf(null);
                          setComposerNotice("");
                        }}
                        className="rounded p-1 text-white/40 transition hover:bg-white/[0.08] hover:text-white"
                      >
                        <X size={13} />
                      </button>
                    </div>
                  </div>
                )}

                <div className="px-4 pb-1 pt-4 sm:px-5">
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    value={input}
                    onChange={handleTextareaChange}
                    onKeyDown={handleComposerKeyDown}
                    placeholder="Ask Scout anything..."
                    aria-label="Research question"
                    className="max-h-48 min-h-[30px] w-full resize-none bg-transparent text-sm leading-6 text-white outline-none placeholder:text-white/35"
                  />
                </div>

                <div className="flex items-center justify-between gap-2 px-3 pb-3 pt-2 sm:px-4">
                  <div className="flex min-w-0 items-center gap-2">
                    {/* Plus / PDF */}
                    <button
                      type="button"
                      aria-label="Attach a PDF"
                      aria-expanded={attachmentMenuOpen}
                      onClick={() =>
                        setAttachmentMenuOpen((previous) => !previous)
                      }
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border transition ${
                        attachmentMenuOpen
                          ? "border-white/20 bg-white/[0.08] text-white"
                          : "border-white/[0.09] bg-white/[0.025] text-white/60 hover:bg-white/[0.07] hover:text-white"
                      }`}
                    >
                      <Plus size={18} />
                    </button>

                    {/* Deep Research toggle */}
                    <button
                      type="button"
                      aria-pressed={mode === "deep"}
                      onClick={() => {
                        setMode((previous) =>
                          previous === "standard" ? "deep" : "standard"
                        );
                        setComposerNotice("");
                      }}
                      className={`flex h-9 min-w-0 items-center gap-2 rounded-xl border px-3 transition ${
                        mode === "deep"
                          ? "border-cyan-300/35 bg-cyan-300/[0.09] text-cyan-100"
                          : "border-white/[0.09] bg-white/[0.025] text-white/55 hover:border-white/[0.17] hover:text-white/85"
                      }`}
                    >
                      <BrainCircuit
                        size={17}
                        className={
                          mode === "deep"
                            ? "shrink-0 text-cyan-300"
                            : "shrink-0"
                        }
                      />

                      <span className="truncate text-xs font-medium">
                        Deep Research
                      </span>

                      {mode === "deep" && (
                        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(103,232,249,0.7)]" />
                      )}
                    </button>
                  </div>

                  {/* Send */}
                  <button
                    type="button"
                    onClick={() => void handleSend()}
                    disabled={!input.trim() || isSending}
                    aria-label="Send research question"
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-300 text-[#061019] shadow-[0_0_20px_rgba(34,211,238,0.08)] transition hover:bg-cyan-200 hover:shadow-[0_0_25px_rgba(34,211,238,0.16)] disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    {isSending ? (
                      <LoaderCircle size={18} className="animate-spin" />
                    ) : (
                      <ArrowUp size={19} strokeWidth={2.3} />
                    )}
                  </button>
                </div>
              </div>

              {composerNotice && (
                <p className="mt-2 px-2 text-xs leading-5 text-white/50">
                  {composerNotice}
                </p>
              )}

              <p className="mt-3 text-center text-[10px] leading-5 text-white/30">
                Scout can make mistakes. Verify important findings with the
                original sources.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}