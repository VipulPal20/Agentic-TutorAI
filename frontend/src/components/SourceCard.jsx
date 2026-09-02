import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

/**
 * One retrieved passage. Collapsed it shows the filename and a similarity
 * meter; clicking reveals the snippet the agent actually read.
 */
export default function SourceCard({ source }) {
  const [open, setOpen] = useState(false);
  const percent = Math.max(0, Math.min(1, source.score)) * 100;

  return (
    <button
      type="button"
      className="source"
      onClick={() => setOpen((value) => !value)}
      aria-expanded={open}
    >
      <span className="source__name">
        [{source.rank}] {source.source}
      </span>
      <span className="source__score">{source.score.toFixed(3)}</span>

      <span className="source__meter" aria-hidden="true">
        <motion.i
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.5, ease: [0.22, 0.61, 0.36, 1] }}
        />
      </span>

      <AnimatePresence initial={false}>
        {open && source.snippet && (
          <motion.p
            className="source__snippet"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 0.61, 0.36, 1] }}
          >
            {source.snippet}
          </motion.p>
        )}
      </AnimatePresence>
    </button>
  );
}
