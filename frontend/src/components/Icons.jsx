/**
 * Inline icons. Small enough to keep local — no icon dependency, and every
 * glyph inherits currentColor so it follows the theme.
 */

const base = {
  width: 16,
  height: 16,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": "true",
};

export function ArrowUp() {
  return (
    <svg {...base}>
      <path d="M12 19V5" />
      <path d="M5 12l7-7 7 7" />
    </svg>
  );
}

export function Stop() {
  return (
    <svg {...base}>
      <rect x="7" y="7" width="10" height="10" rx="1.5" />
    </svg>
  );
}

export function Download() {
  return (
    <svg {...base}>
      <path d="M12 3v12" />
      <path d="M7 11l5 5 5-5" />
      <path d="M5 21h14" />
    </svg>
  );
}

export function Notes() {
  return (
    <svg {...base}>
      <path d="M5 3h11l3 3v15H5z" />
      <path d="M9 9h7M9 13h7M9 17h4" />
    </svg>
  );
}

export function Sun() {
  return (
    <svg {...base}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

export function Moon() {
  return (
    <svg {...base}>
      <path d="M20 14.5A8.5 8.5 0 019.5 4a7 7 0 108.9 10.5z" />
    </svg>
  );
}

export function Close() {
  return (
    <svg {...base}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function Reset() {
  return (
    <svg {...base}>
      <path d="M3 12a9 9 0 1015.5-6.2" />
      <path d="M21 3v6h-6" />
    </svg>
  );
}
