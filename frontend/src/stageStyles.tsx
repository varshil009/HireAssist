/** Stage label styling (background on stage name only). */

const LABEL_TO_STAGE: Record<string, number> = {
  rejected: -1,
  applied: 0,
  screening: 1,
  offered: 2,
  hired: 3,
};

export function stageFromLabel(label: string): number | null {
  const key = label
    .toLowerCase()
    .replace(/[✓✔]/g, "")
    .trim();
  if (key in LABEL_TO_STAGE) return LABEL_TO_STAGE[key];
  if (key === "start") return null;
  return null;
}

export function stagePillClass(stage: number): string {
  switch (stage) {
    case 0:
      return "bg-sky-300 text-sky-950";
    case 1:
      return "bg-yellow-300 text-yellow-950";
    case 2:
      return "bg-lime-200 text-lime-950";
    case 3:
      return "bg-green-600 text-white";
    case -1:
      return "bg-red-400 text-red-950";
    default:
      return "bg-slate-200 text-slate-800";
  }
}

export function stageDisplayText(label: string, stage: number): string {
  if (stage === 3 && !label.includes("✓")) {
    return `${label} ✓`;
  }
  return label;
}

type StagePillProps = {
  label: string;
  stage?: number;
  className?: string;
};

export function StagePill({ label, stage, className = "" }: StagePillProps) {
  const resolved = stage !== undefined ? stage : stageFromLabel(label);
  if (resolved === null) {
    return <span className={className}>{label}</span>;
  }
  return (
    <span
      className={`inline-block rounded-md px-2 py-0.5 text-xs font-semibold leading-tight ${stagePillClass(resolved)} ${className}`}
    >
      {stageDisplayText(label, resolved)}
    </span>
  );
}

export const STAGE_COLUMN_BORDER: Record<number, string> = {
  0: "border-t-sky-400",
  1: "border-t-yellow-400",
  2: "border-t-lime-400",
  3: "border-t-green-600",
  [-1]: "border-t-red-500",
};
