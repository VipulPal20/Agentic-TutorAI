import { useCallback, useEffect, useState } from "react";

const KEY = "arag-theme";

/** Write the attribute and persist it. Safe to call outside React's lifecycle. */
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // Private mode or storage disabled — the theme still applies this session.
  }
}

/**
 * Light/dark theme, persisted to localStorage and applied to <html>.
 * The initial value is set by an inline script in index.html to avoid a flash,
 * so here we just read back what's already on the element.
 */
export default function useTheme() {
  const [theme, setTheme] = useState(() => {
    if (typeof document === "undefined") return "dark";
    return document.documentElement.getAttribute("data-theme") || "dark";
  });

  // Keeps the DOM honest if `theme` ever changes without going through
  // `toggle` (and covers the very first mount).
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggle = useCallback(() => {
    // The attribute is the source of truth, so this needs no `theme` dependency.
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    // Write synchronously, *before* the re-render. Consumers that read the
    // resolved palette with getComputedStyle in an effect (AmbientField) would
    // otherwise see the old theme: child passive effects flush before the
    // parent's, so the effect above lands too late for them.
    applyTheme(next);
    setTheme(next);
  }, []);

  return { theme, toggle };
}
