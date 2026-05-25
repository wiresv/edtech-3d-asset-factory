import { type ReactNode } from "react";

type Tone = "purple" | "red" | "green" | "blue" | "amber" | "neutral";

const tones: Record<Tone, { bg: string; fg: string; dot: string }> = {
  purple: { bg: "bg-accent-purple/10", fg: "text-accent-purple", dot: "bg-accent-purple" },
  red: { bg: "bg-accent-red/10", fg: "text-accent-red", dot: "bg-accent-red" },
  green: { bg: "bg-accent-green/10", fg: "text-accent-green", dot: "bg-accent-green" },
  blue: { bg: "bg-accent-blue/10", fg: "text-accent-blue", dot: "bg-accent-blue" },
  amber: { bg: "bg-accent-amber/10", fg: "text-accent-amber", dot: "bg-accent-amber" },
  neutral: { bg: "bg-surface", fg: "text-muted", dot: "bg-muted-2" },
};

export default function PillBadge({
  tone = "neutral",
  children,
  icon,
  className = "",
}: {
  tone?: Tone;
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  const t = tones[tone];
  return (
    <span
      className={
        `inline-flex items-center gap-1.5 rounded-pill px-2 py-[3px] text-[10.5px] font-semibold uppercase tracking-[0.07em] ${t.bg} ${t.fg} ` +
        className
      }
    >
      {icon ?? <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} aria-hidden />}
      {children}
    </span>
  );
}
