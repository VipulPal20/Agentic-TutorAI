/** Building and saving Markdown files from the conversation. */

function stamp(date = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `-${pad(date.getHours())}${pad(date.getMinutes())}`
  );
}

/** Render the whole conversation — questions, answers, and cited sources. */
export function conversationToMarkdown(turns) {
  const lines = [
    "# Agentic RAG conversation",
    "",
    `_Exported ${new Date().toLocaleString()}_`,
    "",
  ];

  for (const turn of turns) {
    lines.push(`## ${turn.question}`, "");
    lines.push(turn.answer ? turn.answer.trim() : "_No answer was produced._", "");

    if (turn.sources?.length) {
      lines.push("**Sources**", "");
      for (const source of turn.sources) {
        const score = source.score.toFixed(3);
        lines.push(`- \`${source.source}\` — similarity ${score}`);
      }
      lines.push("");
    }
  }

  return lines.join("\n");
}

/** Trigger a download of `text` as a .md file. */
export function downloadMarkdown(text, prefix) {
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${prefix}-${stamp()}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Give the browser a moment to start the download before revoking.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
