/**
 * API client.
 *
 * `/chat` streams Server-Sent Events over a POST, which EventSource can't do,
 * so we read the response body directly and split on the SSE frame delimiter.
 */

const BASE = import.meta.env.VITE_API_BASE ?? "";

/** Raised for non-2xx responses so callers can show the server's message. */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readError(response) {
  try {
    const body = await response.json();
    if (Array.isArray(body.detail)) {
      const messages = body.detail
        .map((item) => item?.msg)
        .filter(Boolean)
        .join("; ");
      if (messages) return messages;
    } else if (typeof body.detail === "string" && body.detail) {
      return body.detail;
    }
    if (typeof body.error === "string" && body.error) return body.error;
    return `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

/** Parse the complete SSE frames in `chunk` and hand each payload to `onEvent`. */
function emitFrames(chunk, onEvent) {
  for (const line of chunk.split("\n")) {
    if (!line.startsWith("data:")) continue;
    const payload = line.slice(5).trim();
    if (!payload) continue;
    try {
      onEvent(JSON.parse(payload));
    } catch {
      // A malformed frame shouldn't kill the stream.
    }
  }
}

/**
 * Stream one agent run.
 *
 * @param {string} query
 * @param {object} options
 * @param {(event: object) => void} options.onEvent called per SSE frame
 * @param {AbortSignal} [options.signal]
 * @param {string} [options.sessionId]
 */
export async function streamChat(query, { onEvent, signal, sessionId } = {}) {
  const response = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId ?? null }),
    signal,
  });

  if (!response.ok) throw new ApiError(await readError(response), response.status);
  if (!response.body) throw new ApiError("This browser can't read streams.", 0);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      buffer += decoder.decode();
      if (buffer.trim()) emitFrames(buffer, onEvent);
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) emitFrames(frame, onEvent);
  }
}

/** Turn a transcript into Markdown notes. */
export async function fetchNotes(turns) {
  const response = await fetch(`${BASE}/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ turns }),
  });
  if (!response.ok) throw new ApiError(await readError(response), response.status);
  const body = await response.json();
  return body.notes;
}

/** Fetch grounded learning content (quizzes, flashcards, explanations, assessments). */
export async function fetchLearnContent({ topic, mode = "quiz", difficulty = "medium", count = 5 } = {}) {
  const response = await fetch(`${BASE}/learn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic: topic || null, mode, difficulty, count }),
  });
  if (!response.ok) throw new ApiError(await readError(response), response.status);
  return response.json();
}

/** Read service health (document count powers the top-bar readout). */
export async function fetchHealth() {
  const response = await fetch(`${BASE}/health`);
  if (!response.ok) throw new ApiError(await readError(response), response.status);
  return response.json();
}

// ---------------------------------------------------------------------------
// Knowledge-base / upload helpers
// ---------------------------------------------------------------------------

/**
 * Upload files into the knowledge base.
 *
 * @param {File[]} files
 * @param {(progress: number) => void} [onProgress] - 0-100 value
 * @returns {Promise<object>}
 */
export async function uploadFiles(files, onProgress) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file, file.name);
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/upload`);

    if (onProgress) {
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      });
    }

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new ApiError("Invalid JSON response from server.", xhr.status));
        }
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          const detail =
            typeof body.detail === "string" ? body.detail : `Upload failed (${xhr.status})`;
          reject(new ApiError(detail, xhr.status));
        } catch {
          reject(new ApiError(`Upload failed (${xhr.status})`, xhr.status));
        }
      }
    });

    xhr.addEventListener("error", () => reject(new ApiError("Network error during upload.", 0)));
    xhr.addEventListener("abort", () => reject(new ApiError("Upload aborted.", 0)));

    xhr.send(formData);
  });
}

/** Fetch the list of sources currently in the knowledge base. */
export async function fetchSources() {
  const response = await fetch(`${BASE}/sources`);
  if (!response.ok) throw new ApiError(await readError(response), response.status);
  return response.json();
}

/** Delete a source (and all its chunks) from the knowledge base. */
export async function deleteSource(sourceName) {
  const encoded = encodeURIComponent(sourceName);
  const response = await fetch(`${BASE}/sources/${encoded}`, { method: "DELETE" });
  if (!response.ok) throw new ApiError(await readError(response), response.status);
  return response.json();
}
