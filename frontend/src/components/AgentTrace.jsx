import { AnimatePresence, motion } from "framer-motion";

/**
 * The agent's live reasoning, drawn as a thread with each step clipped onto it.
 * While the run is active a small pulse travels the thread; when it finishes the
 * pulse goes away and the steps remain as a record of how the answer was found.
 */
export default function AgentTrace({ steps, active }) {
  if (!steps.length) return null;

  return (
    <div className="trace">
      {active && (
        <motion.span
          className="trace__pulse"
          aria-hidden="true"
          initial={{ top: "0.35rem", opacity: 0 }}
          animate={{ top: ["0.35rem", "calc(100% - 0.6rem)"], opacity: [0, 1, 1, 0] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      <ul className="sr-only" aria-live="polite">
        {/* Announce only the latest step so screen readers aren't flooded. */}
        <li>{steps[steps.length - 1].label}</li>
      </ul>

      <AnimatePresence initial={false}>
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          return (
            <motion.div
              key={`${step.stage}-${index}-${step.label}`}
              className={`step${active && isLast ? " step--live" : ""}`}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.28, ease: [0.22, 0.61, 0.36, 1] }}
            >
              <span className="step__mark" aria-hidden="true">
                {active && isLast ? "○" : "•"}
              </span>
              <span>
                {step.label}
                {step.query ? (
                  <span className="step__query"> — “{step.query}”</span>
                ) : null}
              </span>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
