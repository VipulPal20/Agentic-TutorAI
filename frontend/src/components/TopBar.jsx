import { Download, Moon, Notes, Reset, Sun } from "./Icons.jsx";

/** Compact status readout: how many documents are indexed, and DB state. */
function describeHealth(health) {
  if (!health) return "offline";
  const count = health.document_count;
  const docs = count === null || count === undefined ? "—" : count;
  return `${docs} chunks · db ${health.database}`;
}

/**
 * Header: identity on the left, the four toggles on the right
 * (sources, download the chat, summarize as notes, switch theme).
 */
export default function TopBar({
  theme,
  onToggleTheme,
  onDownload,
  onNotes,
  onLearn,
  onReset,
  onSources,
  hasTurns,
  health,
  sourceCount,
}) {
  return (
    <header className="bar">
      <div className="bar__mark">
        <span className="bar__dot" aria-hidden="true" />
        <span className="bar__title">Agentic RAG</span>
      </div>

      <span className="bar__meta">{describeHealth(health)}</span>

      <div className="bar__spacer" />

      <div className="bar__actions">
        {/* Sources / Knowledge base button — always visible */}
        <button
          type="button"
          className="btn btn--sources"
          onClick={onSources}
          title="Manage knowledge base sources"
          id="sources-btn"
        >
          <span className="btn__sources-icon" aria-hidden="true">📚</span>
          <span className="btn__label">Sources</span>
          {sourceCount > 0 && (
            <span className="sources-badge" aria-label={`${sourceCount} sources`}>
              {sourceCount}
            </span>
          )}
        </button>

        {/* Learn Me Button */}
        <button
          type="button"
          className="btn btn--learn"
          onClick={onLearn}
          title="Interactive AI Learning Workspace & Quizzes"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
            <path d="M6 12v5c3 3 9 3 12 0v-5" />
          </svg>
          <span className="btn__label">Learn</span>
        </button>

        <button
          type="button"
          className="btn"
          onClick={onNotes}
          disabled={!hasTurns}
          title="Summarize this conversation as notes"
        >
          <Notes />
          <span className="btn__label">Notes</span>
        </button>

        <button
          type="button"
          className="btn"
          onClick={onDownload}
          disabled={!hasTurns}
          title="Download the conversation as Markdown"
        >
          <Download />
          <span className="btn__label">Export</span>
        </button>

        <button
          type="button"
          className="btn btn--icon"
          onClick={onReset}
          disabled={!hasTurns}
          aria-label="Clear the conversation"
          title="Clear the conversation"
        >
          <Reset />
        </button>

        <button
          type="button"
          className="btn btn--icon"
          onClick={onToggleTheme}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        >
          {theme === "dark" ? <Sun /> : <Moon />}
        </button>
      </div>
    </header>
  );
}
