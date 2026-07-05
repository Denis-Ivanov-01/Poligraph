type MetricIconType =
  | "statements"
  | "politicians"
  | "parties"
  | "score"
  | "methodology"
  | "shield"
  | "compass";

export function MetricIcon({ type }: { type: MetricIconType }) {
  const icons = {
    statements: (
      <>
        <path d="M8 5.5h8" />
        <path d="M8 10h8" />
        <path d="M8 14.5h5" />
        <path d="M5 2.75h14v18.5H5z" />
      </>
    ),
    politicians: (
      <>
        <path d="M8.5 9a3.5 3.5 0 1 0 7 0 3.5 3.5 0 0 0-7 0z" />
        <path d="M5 20c1.2-3.2 3.5-5 7-5s5.8 1.8 7 5" />
      </>
    ),
    parties: (
      <>
        <path d="M4.5 20h15" />
        <path d="M6 17V9l6-4 6 4v8" />
        <path d="M9 17v-5h6v5" />
      </>
    ),
    score: (
      <>
        <path d="M12 3.5l2.4 5 5.5.8-4 3.9.9 5.5L12 16.1l-4.8 2.6.9-5.5-4-3.9 5.5-.8z" />
      </>
    ),
    methodology: (
      <>
        <path d="M5 4.5h14" />
        <path d="M7 8.5h10" />
        <path d="M7 12.5h7" />
        <path d="M6 19.5l4-3 3 2 5-5" />
      </>
    ),
    shield: (
      <>
        <path d="M12 3.5 18.5 6v5.2c0 4.1-2.6 7.4-6.5 9.3-3.9-1.9-6.5-5.2-6.5-9.3V6z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    compass: (
      <>
        <circle cx="12" cy="12" r="8" />
        <path d="m14.8 9.2-1.7 4.1-3.9 1.5 1.7-4.1z" />
      </>
    )
  };

  return (
    <svg className="metric-icon" viewBox="0 0 24 24" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8">
        {icons[type]}
      </g>
    </svg>
  );
}
