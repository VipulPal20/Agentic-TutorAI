import React, { useMemo, useState } from "react";

/**
 * Citation pill badge for citations like 【1†source=filename.pdf】
 */
function CitationPill({ text, onSourceClick }) {
  let label = text;
  let sourceName = "";

  const match = text.match(/(?:(\d+)†)?(?:source=)?([^】]+)/);
  if (match) {
    const num = match[1];
    const src = match[2]?.trim();
    sourceName = src || "";
    label = num ? `${num} · ${src || "Source"}` : src || text;
  }

  const displayLabel = label.length > 28 ? label.slice(0, 25) + "…" : label;

  return (
    <span
      className="citation-pill"
      title={`Source: ${sourceName || text}`}
      onClick={() => onSourceClick?.(sourceName)}
      role="button"
      tabIndex={0}
    >
      <span className="citation-pill__icon">📄</span>
      <span className="citation-pill__text">{displayLabel}</span>
    </span>
  );
}

/**
 * Code block with copy button
 */
function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="md-code-block">
      <div className="md-code-block__header">
        <span className="md-code-block__lang">{language || "text"}</span>
        <button
          type="button"
          className="md-code-block__copy"
          onClick={handleCopy}
          aria-label="Copy code"
        >
          {copied ? "✓ Copied" : "Copy"}
        </button>
      </div>
      <pre className="md-code-block__pre">
        <code>{code}</code>
      </pre>
    </div>
  );
}

/**
 * Parses inline text for bold, italic, code, citations, and links.
 */
function renderInline(text, onSourceClick) {
  if (!text) return null;

  const citationRegex = /【\s*([^】]+?)\s*】/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = citationRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }
    parts.push({ type: "citation", content: match[1] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: "text", content: text.slice(lastIndex) });
  }

  return parts.map((part, pIdx) => {
    if (part.type === "citation") {
      return (
        <CitationPill
          key={`cit-${pIdx}`}
          text={part.content}
          onSourceClick={onSourceClick}
        />
      );
    }

    const textContent = part.content;
    const tokens = [];
    const inlineRegex = /(\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|<br\s*\/?>|•)/g;
    let tLast = 0;
    let tMatch;

    while ((tMatch = inlineRegex.exec(textContent)) !== null) {
      if (tMatch.index > tLast) {
        tokens.push({ type: "plain", val: textContent.slice(tLast, tMatch.index) });
      }

      if (tMatch[2]) {
        tokens.push({ type: "bold", val: tMatch[2] });
      } else if (tMatch[3]) {
        tokens.push({ type: "italic", val: tMatch[3] });
      } else if (tMatch[4]) {
        tokens.push({ type: "code", val: tMatch[4] });
      } else if (tMatch[0].startsWith("<br")) {
        tokens.push({ type: "br" });
      } else if (tMatch[0] === "•") {
        tokens.push({ type: "bullet" });
      }

      tLast = tMatch.index + tMatch[0].length;
    }
    if (tLast < textContent.length) {
      tokens.push({ type: "plain", val: textContent.slice(tLast) });
    }

    return (
      <React.Fragment key={`txt-${pIdx}`}>
        {tokens.map((tok, tIdx) => {
          if (tok.type === "bold") return <strong key={tIdx} className="md-bold">{renderInline(tok.val, onSourceClick)}</strong>;
          if (tok.type === "italic") return <em key={tIdx} className="md-italic">{tok.val}</em>;
          if (tok.type === "code") return <code key={tIdx} className="md-inline-code">{tok.val}</code>;
          if (tok.type === "br") return <br key={tIdx} />;
          if (tok.type === "bullet") return <span key={tIdx} className="md-bullet">• </span>;
          return tok.val;
        })}
      </React.Fragment>
    );
  });
}

/**
 * Full Markdown Document Renderer supporting tables, code blocks, lists, citations, blockquotes.
 */
export default function MarkdownRenderer({ content, onSourceClick }) {
  const blocks = useMemo(() => {
    if (!content) return [];

    const rawLines = content.split("\n");
    const parsedBlocks = [];
    let i = 0;

    while (i < rawLines.length) {
      const line = rawLines[i];

      // 1. Code Block
      if (line.trim().startsWith("```")) {
        const lang = line.trim().slice(3).trim();
        const codeLines = [];
        i += 1;
        while (i < rawLines.length && !rawLines[i].trim().startsWith("```")) {
          codeLines.push(rawLines[i]);
          i += 1;
        }
        parsedBlocks.push({
          type: "codeblock",
          language: lang,
          code: codeLines.join("\n"),
        });
        i += 1;
        continue;
      }

      // 2. Table Block (lines starting with | or containing multiple |)
      if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
        const tableLines = [];
        while (
          i < rawLines.length &&
          rawLines[i].trim().startsWith("|") &&
          rawLines[i].trim().endsWith("|")
        ) {
          tableLines.push(rawLines[i].trim());
          i += 1;
        }

        if (tableLines.length >= 2) {
          const isSep = /^\|(\s*:?-+:?\s*\|)+$/.test(tableLines[1]);
          let headers = [];
          let rows = [];

          if (isSep) {
            headers = tableLines[0]
              .slice(1, -1)
              .split("|")
              .map((c) => c.trim());
            rows = tableLines.slice(2).map((r) =>
              r
                .slice(1, -1)
                .split("|")
                .map((c) => c.trim())
            );
          } else {
            rows = tableLines.map((r) =>
              r
                .slice(1, -1)
                .split("|")
                .map((c) => c.trim())
            );
          }

          parsedBlocks.push({
            type: "table",
            headers,
            rows,
          });
          continue;
        }
      }

      // 3. Headings (#, ##, ###)
      const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
      if (hMatch) {
        parsedBlocks.push({
          type: "heading",
          level: hMatch[1].length,
          text: hMatch[2],
        });
        i += 1;
        continue;
      }

      // 4. Blockquote
      if (line.trim().startsWith(">")) {
        const qLines = [];
        while (i < rawLines.length && rawLines[i].trim().startsWith(">")) {
          qLines.push(rawLines[i].trim().replace(/^>\s?/, ""));
          i += 1;
        }
        parsedBlocks.push({
          type: "blockquote",
          text: qLines.join(" "),
        });
        continue;
      }

      // 5. Unordered List
      if (/^(\s*)[-*+]\s*(.*)$/.test(line) && line.trim().length > 1) {
        const listItems = [];
        while (i < rawLines.length && /^(\s*)[-*+]\s*(.*)$/.test(rawLines[i])) {
          const lMatch = rawLines[i].match(/^(\s*)[-*+]\s*(.*)$/);
          let itemText = (lMatch[2] || "").trim();
          if (!itemText && i + 1 < rawLines.length && rawLines[i + 1].trim() && !/^(\s*)[-*+]/.test(rawLines[i + 1]) && !/^(\s*)\d+\./.test(rawLines[i + 1])) {
            i += 1;
            itemText = rawLines[i].trim();
          }
          if (itemText) listItems.push(itemText);
          i += 1;
        }
        if (listItems.length > 0) {
          parsedBlocks.push({
            type: "ul",
            items: listItems,
          });
          continue;
        }
      }

      // 6. Ordered List
      if (/^(\s*)\d+\.\s*(.*)$/.test(line)) {
        const listItems = [];
        while (i < rawLines.length && /^(\s*)\d+\.\s*(.*)$/.test(rawLines[i])) {
          const lMatch = rawLines[i].match(/^(\s*)\d+\.\s*(.*)$/);
          let itemText = (lMatch[2] || "").trim();
          if (!itemText && i + 1 < rawLines.length && rawLines[i + 1].trim() && !/^(\s*)\d+\./.test(rawLines[i + 1]) && !/^(\s*)[-*+]/.test(rawLines[i + 1])) {
            i += 1;
            itemText = rawLines[i].trim();
          }
          if (itemText) listItems.push(itemText);
          i += 1;
        }
        if (listItems.length > 0) {
          parsedBlocks.push({
            type: "ol",
            items: listItems,
          });
          continue;
        }
      }

      // 7. Plain paragraph
      if (line.trim()) {
        const pLines = [line];
        i += 1;
        while (
          i < rawLines.length &&
          rawLines[i].trim() &&
          !rawLines[i].trim().startsWith("#") &&
          !rawLines[i].trim().startsWith("```") &&
          !rawLines[i].trim().startsWith("|") &&
          !rawLines[i].trim().startsWith(">") &&
          !/^(\s*)[-*+]\s+/.test(rawLines[i]) &&
          !/^(\s*)\d+\.\s+/.test(rawLines[i])
        ) {
          pLines.push(rawLines[i]);
          i += 1;
        }
        parsedBlocks.push({
          type: "paragraph",
          text: pLines.join("\n"),
        });
        continue;
      }

      i += 1;
    }

    return parsedBlocks;
  }, [content]);

  return (
    <div className="md-content">
      {blocks.map((block, idx) => {
        switch (block.type) {
          case "codeblock":
            return (
              <CodeBlock
                key={idx}
                code={block.code}
                language={block.language}
              />
            );

          case "table":
            return (
              <div key={idx} className="md-table-wrapper">
                <table className="md-table">
                  {block.headers.length > 0 && (
                    <thead>
                      <tr>
                        {block.headers.map((h, hIdx) => (
                          <th key={hIdx}>{renderInline(h, onSourceClick)}</th>
                        ))}
                      </tr>
                    </thead>
                  )}
                  <tbody>
                    {block.rows.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {row.map((cell, cIdx) => (
                          <td key={cIdx}>{renderInline(cell, onSourceClick)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );

          case "heading": {
            const Tag = `h${block.level}`;
            return (
              <Tag key={idx} className={`md-h${block.level}`}>
                {renderInline(block.text, onSourceClick)}
              </Tag>
            );
          }

          case "blockquote":
            return (
              <blockquote key={idx} className="md-blockquote">
                {renderInline(block.text, onSourceClick)}
              </blockquote>
            );

          case "ul":
            return (
              <ul key={idx} className="md-ul">
                {block.items.map((item, itIdx) => (
                  <li key={itIdx}>{renderInline(item, onSourceClick)}</li>
                ))}
              </ul>
            );

          case "ol":
            return (
              <ol key={idx} className="md-ol">
                {block.items.map((item, itIdx) => (
                  <li key={itIdx}>{renderInline(item, onSourceClick)}</li>
                ))}
              </ol>
            );

          case "paragraph":
            return (
              <p key={idx} className="md-p">
                {renderInline(block.text, onSourceClick)}
              </p>
            );

          default:
            return null;
        }
      })}
    </div>
  );
}
