import { AnimatePresence, motion } from "framer-motion";

const PROMPTS = [
  "What does the knowledge base say about retrieval-augmented generation?",
  "Summarize how the agent decides whether to search.",
  "Which sources mention embeddings, and what do they claim?",
];

/**
 * First-run state. Sets the tone, shows an upload CTA if no sources are loaded,
 * and offers three starting questions so the empty input isn't the only thing on screen.
 */
export default function Intro({ onPick, onOpenSources, sourceCount }) {
  const hasNoSources = sourceCount === 0;

  return (
    <motion.section
      className="intro"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 0.61, 0.36, 1] }}
    >
      <p className="intro__eyebrow">Retrieval · reasoning · citation</p>
      <h1 className="intro__title">
        Ask your knowledge base.
        <br />
        Watch it <span>think</span>.
      </h1>
      <p className="intro__lead">
        Every answer streams alongside the agent's own trace — which tools it reached
        for, what it retrieved, and how close each passage was.
      </p>

      {/* Upload CTA when no sources exist */}
      {hasNoSources && (
        <motion.div
          className="intro__upload-cta"
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35, delay: 0.2 }}
        >
          <div className="upload-cta__icon" aria-hidden="true">📁</div>
          <div className="upload-cta__body">
            <p className="upload-cta__title">No sources yet</p>
            <p className="upload-cta__sub">
              Upload PDFs, documents, or images to build your knowledge base.
            </p>
          </div>
          <button
            type="button"
            className="btn btn--primary"
            onClick={onOpenSources}
            id="upload-cta-btn"
          >
            Upload sources
          </button>
        </motion.div>
      )}

      <div className="prompts">
        <AnimatePresence initial>
          {PROMPTS.map((prompt, index) => (
            <motion.button
              key={prompt}
              type="button"
              className="prompt"
              onClick={() => onPick(prompt)}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35, delay: 0.1 + index * 0.07 }}
            >
              <span className="prompt__arrow" aria-hidden="true">
                →
              </span>
              <span>{prompt}</span>
            </motion.button>
          ))}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}
