import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

import { Close } from "./Icons.jsx";
import MarkdownRenderer from "./MarkdownRenderer.jsx";

/**
 * LearnPanel — Interactive AI Learning Workspace ("Learn Me")
 * Features:
 * - Interactive Grounded Quiz Mode (1 question at a time, score bar, immediate feedback)
 * - Card-flip Flashcard Mode (front/back 3D rotate, Know It / Review It tracking)
 * - Structured Lesson Explain Mode (Overview, Sections, Misconceptions, Sources)
 * - Adaptive Mastery Profile & Weak Area Gap Detection
 */
export default function LearnPanel({ open, onClose, fetchContent, sources = [] }) {
  const [mode, setMode] = useState("quiz"); // 'quiz' | 'flashcard' | 'explain'
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  // Quiz state
  const [qIndex, setQIndex] = useState(0);
  const [selectedOpt, setSelectedOpt] = useState(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [score, setScore] = useState(0);
  const [userAnswers, setUserAnswers] = useState([]);
  const [quizFinished, setQuizFinished] = useState(false);

  // Flashcard state
  const [cardIndex, setCardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [cardStats, setCardStats] = useState({ known: 0, review: 0 });
  const [cardsFinished, setCardsFinished] = useState(false);

  // Close on Escape
  useEffect(() => {
    if (!open) return undefined;
    function onKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  // Load initial content when opened
  useEffect(() => {
    if (open && !data && !loading) {
      loadContent(mode, topic, difficulty);
    }
  }, [open]);

  const loadContent = async (reqMode, reqTopic, reqDifficulty) => {
    setLoading(true);
    setError(null);
    setData(null);

    // Reset state
    setQIndex(0);
    setSelectedOpt(null);
    setIsAnswered(false);
    setScore(0);
    setUserAnswers([]);
    setQuizFinished(false);

    setCardIndex(0);
    setIsFlipped(false);
    setCardStats({ known: 0, review: 0 });
    setCardsFinished(false);

    try {
      const res = await fetchContent({
        topic: reqTopic || undefined,
        mode: reqMode,
        difficulty: reqDifficulty,
        count: 5,
      });
      setData(res);
    } catch (err) {
      setError(err.message || "Failed to generate learning content.");
    } finally {
      setLoading(false);
    }
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    loadContent(newMode, topic, difficulty);
  };

  const handleTopicSubmit = (e) => {
    e.preventDefault();
    loadContent(mode, topic, difficulty);
  };

  // Quiz Interaction
  const handleSelectOption = (idx) => {
    if (isAnswered) return;
    setSelectedOpt(idx);
    setIsAnswered(true);

    const currentQ = data?.questions?.[qIndex];
    const isCorrect = idx === currentQ.correct_answer;
    if (isCorrect) setScore((s) => s + 1);

    setUserAnswers((prev) => [
      ...prev,
      {
        questionId: currentQ.id,
        selected: idx,
        correct: isCorrect,
        concept: currentQ.concept,
      },
    ]);
  };

  const handleNextQuestion = () => {
    if (qIndex + 1 < (data?.questions?.length || 0)) {
      setQIndex((i) => i + 1);
      setSelectedOpt(null);
      setIsAnswered(false);
    } else {
      setQuizFinished(true);
    }
  };

  // Flashcard Interaction
  const handleFlashcardRating = (known) => {
    setCardStats((prev) => ({
      known: prev.known + (known ? 1 : 0),
      review: prev.review + (known ? 0 : 1),
    }));

    setIsFlipped(false);
    if (cardIndex + 1 < (data?.flashcards?.length || 0)) {
      setCardIndex((i) => i + 1);
    } else {
      setCardsFinished(true);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="scrim"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          />

          <motion.aside
            className="learn-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Learn Me Workspace"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 34 }}
          >
            {/* Header */}
            <div className="learn-panel__head">
              <div className="learn-panel__title-row">
                <div className="learn-panel__icon">
                  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                    <path d="M6 12v5c3 3 9 3 12 0v-5" />
                  </svg>
                </div>
                <div>
                  <h2 className="learn-panel__title">Learn Me</h2>
                </div>
              </div>
              <button
                type="button"
                className="btn btn--icon"
                onClick={onClose}
                aria-label="Close Learn Me"
              >
                <Close />
              </button>
            </div>

            {/* Mode & Topic Control Bar */}
            <div className="learn-controls">
              <div className="learn-tabs">
                <button
                  type="button"
                  className={`learn-tab ${mode === "quiz" ? "learn-tab--active" : ""}`}
                  onClick={() => handleModeChange("quiz")}
                >
                  Interactive Quiz
                </button>
                <button
                  type="button"
                  className={`learn-tab ${mode === "flashcard" ? "learn-tab--active" : ""}`}
                  onClick={() => handleModeChange("flashcard")}
                >
                  Flashcards
                </button>
                <button
                  type="button"
                  className={`learn-tab ${mode === "explain" ? "learn-tab--active" : ""}`}
                  onClick={() => handleModeChange("explain")}
                >
                  Deep Lesson
                </button>
              </div>

              {/* Topic Search & Filters */}
              <form onSubmit={handleTopicSubmit} className="learn-filter-row">
                <input
                  type="text"
                  className="learn-topic-input"
                  placeholder="Topic (e.g. Gradient Descent)..."
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                />

                {mode === "quiz" && (
                  <select
                    className="learn-diff-select"
                    value={difficulty}
                    onChange={(e) => {
                      setDifficulty(e.target.value);
                      loadContent(mode, topic, e.target.value);
                    }}
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                )}

                <button type="submit" className="btn btn--secondary btn--sm" disabled={loading}>
                  Generate
                </button>
              </form>
            </div>

            {/* Main Body */}
            <div className="learn-panel__body">
              {loading && (
                <div className="learn-loading">
                  <span className="spinner" aria-hidden="true" />
                  <p className="learn-loading__text">
                    Mining knowledge base & synthesizing grounded {mode} material…
                  </p>
                </div>
              )}

              {error && !loading && (
                <div className="notice notice--error" role="alert">
                  <span className="notice__mark">!</span>
                  <span>{error}</span>
                </div>
              )}

              {/* QUIZ MODE */}
              {!loading && !error && mode === "quiz" && data?.questions && (
                <div className="quiz-container">
                  {!quizFinished ? (
                    (() => {
                      const q = data.questions[qIndex];
                      const totalQ = data.questions.length;
                      const progressPct = ((qIndex + 1) / totalQ) * 100;

                      return (
                        <div className="quiz-card">
                          {/* Progress Header */}
                          <div className="quiz-header">
                            <span className="quiz-counter">
                              Question {qIndex + 1} of {totalQ}
                            </span>
                            <span className="quiz-score-pill">
                              Score: {score} / {qIndex + (isAnswered ? 1 : 0)}
                            </span>
                          </div>

                          <div className="quiz-progress-track">
                            <div
                              className="quiz-progress-fill"
                              style={{ width: `${progressPct}%` }}
                            />
                          </div>

                          {/* Question Title */}
                          <h3 className="quiz-question">{q.question}</h3>

                          {q.source?.document && (
                            <div className="quiz-source-tag">
                              Source: {q.source.document} {q.source.page ? `(p. ${q.source.page})` : ""}
                            </div>
                          )}

                          {/* Options */}
                          <div className="quiz-options">
                            {q.options.map((opt, idx) => {
                              let optionState = "";
                              if (isAnswered) {
                                if (idx === q.correct_answer) optionState = "opt--correct";
                                else if (idx === selectedOpt) optionState = "opt--wrong";
                                else optionState = "opt--dimmed";
                              }

                              return (
                                <button
                                  key={idx}
                                  type="button"
                                  className={`quiz-opt ${optionState} ${selectedOpt === idx ? "opt--selected" : ""}`}
                                  onClick={() => handleSelectOption(idx)}
                                  disabled={isAnswered}
                                >
                                  <span className="opt-letter">
                                    {String.fromCharCode(65 + idx)}
                                  </span>
                                  <span className="opt-text">{opt}</span>
                                </button>
                              );
                            })}
                          </div>

                          {/* Feedback Box */}
                          {isAnswered && (
                            <motion.div
                              className={`quiz-feedback ${selectedOpt === q.correct_answer ? "quiz-feedback--correct" : "quiz-feedback--wrong"}`}
                              initial={{ opacity: 0, y: 6 }}
                              animate={{ opacity: 1, y: 0 }}
                            >
                              <div className="feedback-status">
                                {selectedOpt === q.correct_answer
                                  ? "✓ Correct Answer!"
                                  : `✕ Incorrect — Correct: ${String.fromCharCode(65 + q.correct_answer)}. ${q.options[q.correct_answer]}`}
                              </div>
                              <p className="feedback-expl">{q.explanation}</p>
                              <button
                                type="button"
                                className="btn btn--primary btn--sm quiz-next-btn"
                                onClick={handleNextQuestion}
                              >
                                {qIndex + 1 < totalQ ? "Next Question →" : "View Final Results"}
                              </button>
                            </motion.div>
                          )}
                        </div>
                      );
                    })()
                  ) : (
                    /* Quiz Results Screen */
                    <div className="quiz-results">
                      <div className="results-badge">Quiz Completed</div>
                      <h2 className="results-title">{data.topic}</h2>

                      <div className="results-score-circle">
                        <span className="score-num">
                          {Math.round((score / data.questions.length) * 100)}%
                        </span>
                        <span className="score-sub">
                          {score} of {data.questions.length} Correct
                        </span>
                      </div>

                      {/* Student Knowledge Profile & Weak Areas */}
                      {data.mastery && (
                        <div className="mastery-box">
                          <h4 className="mastery-title">Mastery Assessment</h4>
                          <div className="mastery-tags">
                            {data.mastery.strong_concepts.map((c, i) => (
                              <span key={i} className="m-tag m-tag--strong">
                                ✓ Strong: {c}
                              </span>
                            ))}
                            {data.mastery.weak_concepts.map((c, i) => (
                              <span key={i} className="m-tag m-tag--weak">
                                ⚠ Needs Work: {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="results-actions">
                        <button
                          type="button"
                          className="btn btn--secondary"
                          onClick={() => loadContent("quiz", topic, difficulty)}
                        >
                          Retry Quiz
                        </button>
                        <button
                          type="button"
                          className="btn btn--primary"
                          onClick={() => handleModeChange("explain")}
                        >
                          Learn Weak Areas
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* FLASHCARD MODE */}
              {!loading && !error && mode === "flashcard" && data?.flashcards && (
                <div className="flashcard-container">
                  {!cardsFinished ? (
                    (() => {
                      const fc = data.flashcards[cardIndex];
                      const totalFc = data.flashcards.length;

                      return (
                        <div className="flashcard-wrap">
                          <div className="card-counter">
                            Card {cardIndex + 1} of {totalFc} • Click card to flip
                          </div>

                          <div
                            className={`flashcard-scene ${isFlipped ? "is-flipped" : ""}`}
                            onClick={() => setIsFlipped(!isFlipped)}
                          >
                            <div className="flashcard-card">
                              {/* Front */}
                              <div className="flashcard-face flashcard-face--front">
                                <span className="card-label">CONCEPT</span>
                                <h3 className="card-concept">{fc.concept}</h3>
                                <p className="card-prompt">{fc.front}</p>
                                <span className="flip-hint">↷ Click to reveal answer</span>
                              </div>

                              {/* Back */}
                              <div className="flashcard-face flashcard-face--back">
                                <span className="card-label">EXPLANATION</span>
                                <p className="card-answer">{fc.back}</p>
                                {fc.source?.document && (
                                  <div className="card-source">
                                    Source: {fc.source.document}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Self Assessment Controls */}
                          <div className="card-rate-bar">
                            <button
                              type="button"
                              className="btn btn--secondary btn--review"
                              onClick={() => handleFlashcardRating(false)}
                            >
                              Review It
                            </button>
                            <button
                              type="button"
                              className="btn btn--primary btn--know"
                              onClick={() => handleFlashcardRating(true)}
                            >
                              Know It ✓
                            </button>
                          </div>
                        </div>
                      );
                    })()
                  ) : (
                    <div className="cards-finished">
                      <h3>Flashcard Session Completed</h3>
                      <p>
                        Mastered: <strong>{cardStats.known}</strong> | Needs Review:{" "}
                        <strong>{cardStats.review}</strong>
                      </p>
                      <button
                        type="button"
                        className="btn btn--primary"
                        onClick={() => loadContent("flashcard", topic, difficulty)}
                      >
                        Restart Flashcards
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* EXPLAIN MODE */}
              {!loading && !error && mode === "explain" && data?.explanation && (
                <div className="explain-container">
                  <div className="explain-header">
                    <span className="explain-badge">GROUNDED LESSON</span>
                    <h2 className="explain-title">{data.explanation.topic}</h2>
                    <p className="explain-overview">{data.explanation.overview}</p>
                  </div>

                  {data.explanation.sections?.map((sec, idx) => (
                    <div key={idx} className="explain-section">
                      <h4 className="explain-section__title">{sec.title}</h4>
                      <MarkdownRenderer content={sec.content} />
                    </div>
                  ))}

                  {data.explanation.key_takeaways?.length > 0 && (
                    <div className="takeaways-box">
                      <h4 className="box-title">Key Takeaways</h4>
                      <ul>
                        {data.explanation.key_takeaways.map((t, i) => (
                          <li key={i}>{t}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {data.explanation.misconceptions?.length > 0 && (
                    <div className="misconceptions-box">
                      <h4 className="box-title">Common Misconceptions</h4>
                      <ul>
                        {data.explanation.misconceptions.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
