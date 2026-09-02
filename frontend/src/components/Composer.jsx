import { useEffect, useRef } from "react";

import { ArrowUp, Stop } from "./Icons.jsx";

const MAX_HEIGHT = 144; // keep in sync with .composer textarea max-height (9rem)

/**
 * The input. Grows with its content up to a ceiling, submits on Enter, and
 * turns into a stop button while a run is streaming.
 */
export default function Composer({ value, onChange, onSubmit, onStop, busy }) {
  const ref = useRef(null);

  // Autosize: reset then measure, so deleting text shrinks the box too.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  useEffect(() => {
    if (!busy) ref.current?.focus();
  }, [busy]);

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!busy) onSubmit();
    }
  }

  const canSend = value.trim().length > 0;

  return (
    <div className="composer">
      <div className="composer__inner">
        <form
          className="composer__field"
          onSubmit={(event) => {
            event.preventDefault();
            if (!busy && canSend) onSubmit();
          }}
        >
          <label className="sr-only" htmlFor="composer-input">
            Ask a question
          </label>
          <textarea
            id="composer-input"
            ref={ref}
            rows={1}
            value={value}
            placeholder="Ask the knowledge base…"
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
          />

          {busy ? (
            <button
              type="button"
              className="send send--stop"
              onClick={onStop}
              aria-label="Stop generating"
              title="Stop generating"
            >
              <Stop />
            </button>
          ) : (
            <button
              type="submit"
              className="send"
              disabled={!canSend}
              aria-label="Send question"
              title="Send question"
            >
              <ArrowUp />
            </button>
          )}
        </form>

        <div className="composer__hint">
          <span>enter to send · shift+enter for a new line</span>
          <span>{busy ? "streaming…" : "gemini · pgvector"}</span>
        </div>
      </div>
    </div>
  );
}
