import { AnimatePresence, MotionConfig, motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";

import AmbientField from "./components/AmbientField.jsx";
import Composer from "./components/Composer.jsx";
import Intro from "./components/Intro.jsx";
import KnowledgePanel from "./components/KnowledgePanel.jsx";
import Message from "./components/Message.jsx";
import LearnPanel from "./components/LearnPanel.jsx";
import NotesPanel from "./components/NotesPanel.jsx";
import TopBar from "./components/TopBar.jsx";
import useTheme from "./hooks/useTheme.js";
import { fetchHealth, fetchLearnContent, fetchNotes, fetchSources, streamChat } from "./lib/api.js";
import { conversationToMarkdown, downloadMarkdown } from "./lib/download.js";

// How close to the bottom counts as "following the stream".
const PIN_SLACK_PX = 120;

function newSessionId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `s-${Date.now().toString(36)}`;
}

function isNearBottom() {
  const doc = document.documentElement;
  return doc.scrollHeight - (window.scrollY + window.innerHeight) < PIN_SLACK_PX;
}

/**
 * Merge a `sources` batch into the ones already collected.
 */
function mergeSources(existing, incoming) {
  if (!incoming?.length) return existing;

  const seen = new Set(existing.map((item) => `${item.source}\0${item.snippet}`));
  const merged = [...existing];

  for (const item of incoming) {
    const fingerprint = `${item.source}\0${item.snippet}`;
    if (seen.has(fingerprint)) continue;
    seen.add(fingerprint);
    merged.push({ ...item, uid: `${merged.length}-${item.source}` });
  }
  return merged;
}

function emptyTurn(question) {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    question,
    answer: "",
    steps: [],
    sources: [],
    error: null,
    complete: false,
  };
}

export default function App() {
  const { theme, toggle } = useTheme();
  const reduceMotion = useReducedMotion();

  const [turns, setTurns] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState(null);
  const [toast, setToast] = useState(null);

  const [learnOpen, setLearnOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesError, setNotesError] = useState(null);
  const [pinnedNotes, setPinnedNotes] = useState([]);

  // Knowledge base state
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [sources, setSources] = useState([]);

  const [sessionId] = useState(newSessionId);
  const abortRef = useRef(null);
  const bottomRef = useRef(null);
  const busyRef = useRef(false);
  const turnCountRef = useRef(0);

  /* ---- health readout in the top bar ---- */
  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((data) => {
        if (!cancelled) setHealth(data);
      })
      .catch(() => {
        if (!cancelled) setHealth(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  /* ---- load sources on mount ---- */
  const refreshSources = useCallback(() => {
    fetchSources()
      .then((data) => setSources(data.sources ?? []))
      .catch(() => setSources([]));
  }, []);

  useEffect(() => {
    refreshSources();
  }, [refreshSources]);

  /* ---- follow the stream ---- */
  useEffect(() => {
    const isNewTurn = turns.length !== turnCountRef.current;
    turnCountRef.current = turns.length;

    if (isNewTurn) {
      bottomRef.current?.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "end",
      });
      return;
    }
    if (isNearBottom()) {
      bottomRef.current?.scrollIntoView({ behavior: "auto", block: "end" });
    }
  }, [turns, reduceMotion]);

  /* ---- transient toast ---- */
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  /** Apply one SSE frame to the turn currently being answered. */
  const applyEvent = useCallback((turnId, event) => {
    setTurns((current) =>
      current.map((turn) => {
        if (turn.id !== turnId) return turn;

        switch (event.type) {
          case "status":
          case "step":
            return {
              ...turn,
              steps: [
                ...turn.steps,
                {
                  stage: event.stage ?? "step",
                  label: event.label ?? event.stage ?? "Working",
                  query: event.query ?? null,
                },
              ],
            };
          case "sources":
            return { ...turn, sources: mergeSources(turn.sources, event.items) };
          case "token":
            return { ...turn, answer: turn.answer + (event.content ?? "") };
          case "done":
            return { ...turn, complete: true };
          case "error":
            return { ...turn, error: event.detail || "The agent run failed.", complete: true };
          default:
            return turn;
        }
      }),
    );
  }, []);

  const ask = useCallback(
    async (question) => {
      const text = question.trim();
      if (!text || busyRef.current) return;

      const turn = emptyTurn(text);
      setTurns((current) => [...current, turn]);
      setDraft("");
      busyRef.current = true;
      setBusy(true);

      const controller = new AbortController();
      abortRef.current = controller;

      let closed = false;

      try {
        await streamChat(text, {
          sessionId,
          signal: controller.signal,
          onEvent: (event) => {
            if (event.type === "done" || event.type === "error") closed = true;
            applyEvent(turn.id, event);
          },
        });
        if (!closed) {
          applyEvent(turn.id, {
            type: "error",
            detail: "Connection lost before the answer finished.",
          });
        }
      } catch (error) {
        if (error.name === "AbortError") {
          applyEvent(turn.id, { type: "step", stage: "stopped", label: "Stopped" });
          applyEvent(turn.id, { type: "done" });
        } else {
          applyEvent(turn.id, { type: "error", detail: error.message });
        }
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        busyRef.current = false;
        setBusy(false);
      }
    },
    [applyEvent, sessionId],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setTurns([]);
    setNotes("");
    setNotesError(null);
    setToast("Conversation cleared");
  }, []);

  const exportChat = useCallback(() => {
    if (!turns.length) return;
    downloadMarkdown(conversationToMarkdown(turns), "agentic-rag-chat");
    setToast("Conversation saved as Markdown");
  }, [turns]);

  const openNotes = useCallback(async () => {
    if (!turns.length) return;
    setNotesOpen(true);
    setNotesLoading(true);
    setNotesError(null);

    const transcript = [];
    for (const turn of turns) {
      transcript.push({ role: "user", content: turn.question });
      if (turn.answer.trim()) {
        transcript.push({ role: "assistant", content: turn.answer.trim() });
      }
    }

    try {
      setNotes(await fetchNotes(transcript));
    } catch (error) {
      setNotesError(error.message);
    } finally {
      setNotesLoading(false);
    }
  }, [turns]);

  const closeNotes = useCallback(() => setNotesOpen(false), []);

  const exportNotes = useCallback(() => {
    if (!notes) return;
    downloadMarkdown(notes, "agentic-rag-notes");
    setToast("Notes saved as Markdown");
  }, [notes]);

  const openKnowledge = useCallback(() => setKnowledgeOpen(true), []);
  const closeKnowledge = useCallback(() => setKnowledgeOpen(false), []);

  const handleSourcesChanged = useCallback(() => {
    refreshSources();
    // Also refresh health to update chunk count
    fetchHealth()
      .then(setHealth)
      .catch(() => {});
  }, [refreshSources]);

  const handlePinToNotes = useCallback((pin) => {
    setPinnedNotes((prev) => [pin, ...prev]);
    setToast("Pinned to Studio Notes!");
  }, []);

  const handleUpdateNotes = useCallback((newNotes) => {
    setNotes(newNotes);
  }, []);

  return (
    <MotionConfig reducedMotion="user">
      <AmbientField theme={theme} />

      <div className="shell">
        <TopBar
          theme={theme}
          onToggleTheme={toggle}
          onDownload={exportChat}
          onNotes={openNotes}
          onLearn={() => setLearnOpen(true)}
          onReset={reset}
          onSources={openKnowledge}
          hasTurns={turns.length > 0}
          health={health}
          sourceCount={sources.length}
        />

        <main className="thread">
          {turns.length === 0 ? (
            <Intro
              onPick={(prompt) => ask(prompt)}
              onOpenSources={openKnowledge}
              sourceCount={sources.length}
            />
          ) : (
            turns.map((turn, index) => (
              <Message
                key={turn.id}
                turn={turn}
                streaming={busy && index === turns.length - 1 && !turn.complete}
                onPinToNotes={handlePinToNotes}
                onOpenSource={openKnowledge}
              />
            ))
          )}
          <div ref={bottomRef} />
        </main>

        <Composer
          value={draft}
          onChange={setDraft}
          onSubmit={() => ask(draft)}
          onStop={stop}
          busy={busy}
        />
      </div>

      <LearnPanel
        open={learnOpen}
        onClose={() => setLearnOpen(false)}
        fetchContent={fetchLearnContent}
        sources={sources}
      />

      <NotesPanel
        open={notesOpen}
        notes={notes}
        loading={notesLoading}
        error={notesError}
        onClose={closeNotes}
        onDownload={exportNotes}
        onUpdateNotes={handleUpdateNotes}
        pinnedNotes={pinnedNotes}
      />

      <KnowledgePanel
        open={knowledgeOpen}
        sources={sources}
        onClose={closeKnowledge}
        onSourcesChanged={handleSourcesChanged}
      />

      <AnimatePresence>
        {toast && (
          <motion.div
            className="toast"
            role="status"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.2 }}
          >
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </MotionConfig>
  );
}
