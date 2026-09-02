import { useState } from "react";
import { motion } from "framer-motion";

import AgentTrace from "./AgentTrace.jsx";
import MarkdownRenderer from "./MarkdownRenderer.jsx";
import SourceCard from "./SourceCard.jsx";

/**
 * A single question/answer turn: the question, the live trace of how the
 * agent worked, the passages it retrieved, and the answer itself.
 */
export default function Message({ turn, streaming, onPinToNotes, onOpenSource }) {
  const [copied, setCopied] = useState(false);
  const [pinned, setPinned] = useState(false);

  const showCaret = streaming && !turn.error;
  const hasAnswer = Boolean(turn.answer);

  const handleCopy = () => {
    if (!turn.answer) return;
    navigator.clipboard.writeText(turn.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePin = () => {
    if (!turn.answer) return;
    onPinToNotes?.({ question: turn.question, answer: turn.answer });
    setPinned(true);
    setTimeout(() => setPinned(false), 2000);
  };

  return (
    <motion.article
      className="turn"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* User Question */}
      <div className="ask">
        <div className="ask__avatar">
          <span className="ask__avatar-dot" />
          <span className="ask__tag">YOU</span>
        </div>
        <div className="ask__bubble">
          <p className="ask__text">{turn.question}</p>
        </div>
      </div>

      {/* Assistant Answer Box */}
      <div className="answer">
        <div className="answer__header">
          <div className="answer__badge">
            <svg className="answer__sparkle-icon" viewBox="0 0 16 16" width="12" height="12" fill="currentColor">
              <path d="M8 0L9.8 5.6L16 8L9.8 10.4L8 16L6.2 10.4L0 8L6.2 5.6L8 0Z" />
            </svg>
            <span className="answer__badge-text">AGENT RESPONSE</span>
          </div>
        </div>

        {/* Live Reasoning Agent Trace */}
        <AgentTrace steps={turn.steps} active={streaming} />

        {/* Retrieved Source Snippets */}
        {turn.sources.length > 0 && (
          <div className="sources-container">
            <div className="sources-container__label">
              <span>Retrieved context from {turn.sources.length} passage{turn.sources.length !== 1 ? "s" : ""}:</span>
            </div>
            <div className="sources">
              {turn.sources.map((source, index) => (
                <SourceCard key={source.uid ?? index} source={source} />
              ))}
            </div>
          </div>
        )}

        {/* Formatted Answer Body */}
        {(hasAnswer || showCaret) && (
          <div className="answer__body">
            <MarkdownRenderer
              content={turn.answer}
              onSourceClick={onOpenSource}
            />
            {showCaret && <span className="caret" aria-hidden="true" />}
          </div>
        )}

        {/* Error Notice */}
        {turn.error && (
          <div className="notice" role="alert">
            <span className="notice__mark" aria-hidden="true">
              !
            </span>
            <span>{turn.error}</span>
          </div>
        )}

        {/* Message Action Toolbar */}
        {hasAnswer && !streaming && (
          <div className="answer__actions">
            <button
              type="button"
              className={`action-btn ${copied ? "action-btn--active" : ""}`}
              onClick={handleCopy}
              title="Copy answer to clipboard"
            >
              <span>{copied ? "✓ Copied" : "Copy"}</span>
            </button>

            <button
              type="button"
              className={`action-btn ${pinned ? "action-btn--active" : ""}`}
              onClick={handlePin}
              title="Pin this answer into your Studio Notes"
            >
              <span>{pinned ? "✓ Pinned" : "Pin to Notes"}</span>
            </button>
          </div>
        )}
      </div>
    </motion.article>
  );
}
