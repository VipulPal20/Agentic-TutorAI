import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

import { Close, Download } from "./Icons.jsx";
import MarkdownRenderer from "./MarkdownRenderer.jsx";

/**
 * NotesPanel — NotebookLM-style Studio Notes.
 *
 * Features:
 * - AI Generated Study Notes & Summaries
 * - Interactive Editable Markdown Notes & Scratchpad
 * - Pinned Chat Insights
 * - One-click Markdown Export & Clipboard Copy
 */
export default function NotesPanel({
  open,
  notes,
  loading,
  error,
  onClose,
  onDownload,
  onUpdateNotes,
  pinnedNotes = [],
}) {
  const [activeTab, setActiveTab] = useState("summary"); // 'summary' | 'scratchpad'
  const [isEditing, setIsEditing] = useState(false);
  const [localText, setLocalText] = useState(notes || "");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setLocalText(notes || "");
  }, [notes]);

  // Escape closes the drawer
  useEffect(() => {
    if (!open) return undefined;
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  const handleCopy = () => {
    const textToCopy = activeTab === "summary" ? notes : localText;
    if (!textToCopy) return;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveEdit = () => {
    setIsEditing(false);
    onUpdateNotes?.(localText);
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="scrim"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          />

          {/* Sliding Panel */}
          <motion.aside
            className="notes-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Studio Notes"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 34 }}
          >
            {/* Header */}
            <div className="notes-panel__head">
              <div className="notes-panel__title-row">
                <span className="notes-panel__icon">✦</span>
                <div>
                  <h2 className="notes-panel__title">Studio Notes</h2>
                </div>
              </div>
              <button
                type="button"
                className="btn btn--icon"
                onClick={onClose}
                aria-label="Close notes"
              >
                <Close />
              </button>
            </div>

            {/* Studio Navigation Tabs */}
            <div className="notes-tabs">
              <button
                type="button"
                className={`notes-tab ${activeTab === "summary" ? "notes-tab--active" : ""}`}
                onClick={() => setActiveTab("summary")}
              >
                <span>◈ AI Summary</span>
              </button>
              <button
                type="button"
                className={`notes-tab ${activeTab === "scratchpad" ? "notes-tab--active" : ""}`}
                onClick={() => setActiveTab("scratchpad")}
              >
                <span>◐ Scratchpad {pinnedNotes.length > 0 && `(${pinnedNotes.length})`}</span>
              </button>
            </div>

            {/* Main Body */}
            <div className="notes-panel__body">
              {activeTab === "summary" && (
                <>
                  {loading && (
                    <div className="notes-loading">
                      <span className="spinner" aria-hidden="true" />
                      <p className="notes-loading__text">Synthesizing study notes from your chat & sources…</p>
                    </div>
                  )}

                  {error && !loading && (
                    <div className="notice notice--error" role="alert">
                      <span className="notice__mark">!</span>
                      <span>{error}</span>
                    </div>
                  )}

                  {!notes && !loading && !error && (
                    <div className="notes-empty">
                      <div className="notes-empty__icon">✦</div>
                      <p className="notes-empty__title">No Study Notes Yet</p>
                      <p className="notes-empty__desc">
                        Chat with your documents, then open this panel to automatically distill key takeaways, concepts, and citations!
                      </p>
                    </div>
                  )}

                  {notes && !loading && (
                    <div className="notes-content">
                      <MarkdownRenderer content={notes} />
                    </div>
                  )}
                </>
              )}

              {activeTab === "scratchpad" && (
                <div className="scratchpad">
                  {/* Pinned Notes Section */}
                  {pinnedNotes.length > 0 && (
                    <div className="pinned-section">
                      <h4 className="pinned-section__title">◆ Pinned from Chat</h4>
                      <div className="pinned-list">
                        {pinnedNotes.map((pin, idx) => (
                          <div key={idx} className="pin-card">
                            <div className="pin-card__q">Q: {pin.question}</div>
                            <div className="pin-card__a">
                              <MarkdownRenderer content={pin.answer} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Freeform Editor */}
                  <div className="scratchpad-editor-wrap">
                    <div className="scratchpad-header">
                      <span>Personal Notes</span>
                      <button
                        type="button"
                        className="btn-tiny"
                        onClick={() => (isEditing ? handleSaveEdit() : setIsEditing(true))}
                      >
                        {isEditing ? "✓ Done" : "Edit"}
                      </button>
                    </div>

                    {isEditing ? (
                      <textarea
                        className="scratchpad-textarea"
                        value={localText}
                        onChange={(e) => setLocalText(e.target.value)}
                        placeholder="Type your own notes, research thoughts, or synthesis here in Markdown..."
                        rows={12}
                      />
                    ) : (
                      <div className="scratchpad-preview">
                        {localText ? (
                          <MarkdownRenderer content={localText} />
                        ) : (
                          <p className="scratchpad-placeholder">
                            Click 'Edit' above to write custom notes or paste research thoughts...
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Footer Toolbar */}
            <div className="notes-panel__foot">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={handleCopy}
                disabled={(!notes && activeTab === "summary") || loading}
              >
                <span>{copied ? "✓ Copied" : "Copy Notes"}</span>
              </button>

              <button
                type="button"
                className="btn btn--primary"
                onClick={onDownload}
                disabled={!notes || loading}
              >
                <Download />
                <span>Save Notes (.md)</span>
              </button>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
