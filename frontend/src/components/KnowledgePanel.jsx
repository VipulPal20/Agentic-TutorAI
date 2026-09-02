/**
 * KnowledgePanel — NotebookLM-style slide-in sources sidebar.
 *
 * Features:
 *  - Drag-and-drop + click-to-browse file upload
 *  - Per-file upload progress and status
 *  - List of all ingested sources with chunk count
 *  - Per-source delete button
 */

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useRef, useState } from "react";

import { deleteSource, uploadFiles } from "../lib/api.js";

// ---- File-type helpers --------------------------------------------------------

const EXT_LABELS = {
  pdf: "PDF",
  txt: "TXT",
  md: "MD",
  docx: "DOCX",
  png: "IMG",
  jpg: "IMG",
  jpeg: "IMG",
  webp: "IMG",
};

const EXT_COLORS = {
  pdf: "badge--pdf",
  txt: "badge--txt",
  md: "badge--md",
  docx: "badge--docx",
  png: "badge--img",
  jpg: "badge--img",
  jpeg: "badge--img",
  webp: "badge--img",
};

function getExt(filename) {
  return filename.split(".").pop().toLowerCase();
}

function FileBadge({ filename }) {
  const ext = getExt(filename);
  return (
    <span className={`file-badge ${EXT_COLORS[ext] ?? "badge--txt"}`}>
      {EXT_LABELS[ext] ?? ext.toUpperCase()}
    </span>
  );
}

// ---- Upload queue item --------------------------------------------------------

function UploadItem({ item }) {
  return (
    <motion.div
      className={`upload-item upload-item--${item.status}`}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.22 }}
    >
      <div className="upload-item__row">
        <FileBadge filename={item.name} />
        <span className="upload-item__name">{item.name}</span>
        <span className="upload-item__state">
          {item.status === "uploading" && `${item.progress}%`}
          {item.status === "processing" && "Processing…"}
          {item.status === "ok" && `✓ ${item.chunks} chunks`}
          {item.status === "error" && "✗ failed"}
        </span>
      </div>
      {item.status === "uploading" && (
        <div className="upload-bar">
          <div className="upload-bar__fill" style={{ width: `${item.progress}%` }} />
        </div>
      )}
      {item.status === "error" && item.detail && (
        <p className="upload-item__error">{item.detail}</p>
      )}
    </motion.div>
  );
}

// ---- Source item in the knowledge list ----------------------------------------

function SourceRow({ source, onDelete }) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = useCallback(async () => {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    setDeleting(true);
    try {
      await onDelete(source.source);
    } finally {
      setDeleting(false);
      setConfirming(false);
    }
  }, [confirming, onDelete, source.source]);

  return (
    <motion.div
      className="source-row"
      layout
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -12, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.22 }}
    >
      <div className="source-row__info">
        <FileBadge filename={source.source} />
        <span className="source-row__name" title={source.source}>
          {source.source}
        </span>
      </div>
      <div className="source-row__meta">
        <span className="source-row__chunks">{source.chunk_count} chunks</span>
        <button
          className={`source-row__del ${confirming ? "source-row__del--confirm" : ""}`}
          onClick={handleDelete}
          disabled={deleting}
          title={confirming ? "Click again to confirm" : "Remove from knowledge base"}
        >
          {deleting ? "…" : confirming ? "Sure?" : "✕"}
        </button>
      </div>
    </motion.div>
  );
}

// ---- Drop zone ----------------------------------------------------------------

const ACCEPTED = ".pdf,.txt,.md,.docx,.png,.jpg,.jpeg,.webp";

function DropZone({ onFiles, uploading }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      if (uploading) return;
      const files = Array.from(e.dataTransfer.files);
      if (files.length) onFiles(files);
    },
    [onFiles, uploading],
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => setDragOver(false), []);

  const handleChange = useCallback(
    (e) => {
      const files = Array.from(e.target.files ?? []);
      if (files.length) onFiles(files);
      e.target.value = "";
    },
    [onFiles],
  );

  return (
    <div
      className={`drop-zone ${dragOver ? "drop-zone--over" : ""} ${uploading ? "drop-zone--busy" : ""}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => !uploading && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && !uploading && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED}
        className="sr-only"
        onChange={handleChange}
      />
      <div className="drop-zone__icon">{uploading ? "⏳" : "📎"}</div>
      <p className="drop-zone__label">
        {uploading ? "Uploading…" : "Drop files here or click to browse"}
      </p>
      <p className="drop-zone__hint">PDF · TXT · MD · DOCX · PNG · JPG · WEBP · max 50 MB</p>
    </div>
  );
}

// ---- Main panel ---------------------------------------------------------------

export default function KnowledgePanel({ open, sources, onClose, onSourcesChanged }) {
  const [uploads, setUploads] = useState([]);
  const [uploading, setUploading] = useState(false);

  const updateUpload = useCallback((name, patch) => {
    setUploads((prev) =>
      prev.map((u) => (u.name === name ? { ...u, ...patch } : u)),
    );
  }, []);

  const handleFiles = useCallback(
    async (files) => {
      const newItems = files.map((f) => ({
        name: f.name,
        status: "uploading",
        progress: 0,
        chunks: 0,
        detail: null,
      }));
      setUploads((prev) => [...newItems, ...prev]);
      setUploading(true);

      // Track progress per batch (XHR gives one progress for all files)
      const onProgress = (pct) => {
        for (const f of files) updateUpload(f.name, { progress: pct });
      };

      try {
        // Mark as processing once bytes are sent
        for (const f of files) updateUpload(f.name, { status: "processing", progress: 100 });

        const result = await uploadFiles(files, onProgress);

        for (const item of result.uploaded) {
          if (item.status === "ok") {
            updateUpload(item.filename, {
              status: "ok",
              chunks: item.chunks_stored,
            });
          } else {
            updateUpload(item.filename, {
              status: "error",
              detail: item.detail ?? "Ingestion failed",
            });
          }
        }
        onSourcesChanged();
      } catch (err) {
        for (const f of files) {
          updateUpload(f.name, { status: "error", detail: err.message });
        }
      } finally {
        setUploading(false);
      }
    },
    [onSourcesChanged, updateUpload],
  );

  const handleDelete = useCallback(
    async (sourceName) => {
      await deleteSource(sourceName);
      onSourcesChanged();
    },
    [onSourcesChanged],
  );

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="scrim"
            key="kb-scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.aside
            key="kb-panel"
            className="kb-panel"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 340, damping: 36 }}
          >
            {/* Header */}
            <div className="kb-panel__head">
              <div className="kb-panel__title-row">
                <span className="kb-panel__icon">🧠</span>
                <span className="kb-panel__title">Knowledge Base</span>
                {sources.length > 0 && (
                  <span className="kb-panel__count">{sources.length} source{sources.length !== 1 ? "s" : ""}</span>
                )}
              </div>
              <button className="btn btn--icon" onClick={onClose} aria-label="Close">
                ✕
              </button>
            </div>

            {/* Body */}
            <div className="kb-panel__body">
              <DropZone onFiles={handleFiles} uploading={uploading} />

              {/* Upload queue */}
              <AnimatePresence>
                {uploads.length > 0 && (
                  <motion.div
                    className="kb-section"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <p className="kb-section__label">Recent uploads</p>
                    <AnimatePresence>
                      {uploads.map((u) => (
                        <UploadItem key={u.name + u.status} item={u} />
                      ))}
                    </AnimatePresence>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Sources list */}
              <div className="kb-section">
                <p className="kb-section__label">
                  {sources.length === 0 ? "No sources yet" : "Indexed sources"}
                </p>

                {sources.length === 0 ? (
                  <div className="kb-empty">
                    <p className="kb-empty__text">
                      Upload your first document above. The AI will answer questions exclusively from
                      what you add here.
                    </p>
                  </div>
                ) : (
                  <AnimatePresence>
                    {sources.map((s) => (
                      <SourceRow key={s.source} source={s} onDelete={handleDelete} />
                    ))}
                  </AnimatePresence>
                )}
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
