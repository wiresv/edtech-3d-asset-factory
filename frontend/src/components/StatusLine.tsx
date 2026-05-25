export type StatusTone = "idle" | "busy" | "ok" | "error";

export default function StatusLine({
  text,
  tone = "idle",
}: {
  text: string;
  tone?: StatusTone;
}) {
  if (!text) return <div className="h-[18px]" />;
  const color =
    tone === "error"
      ? "text-accent-red"
      : tone === "ok"
        ? "text-accent-green"
        : tone === "busy"
          ? "text-ink-2"
          : "text-muted";
  return (
    <div className={`flex items-start gap-2 text-[12.5px] leading-snug ${color}`}>
      {tone === "busy" ? (
        <span className="relative mt-1 flex h-2 w-2 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/40" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
        </span>
      ) : tone === "ok" ? (
        <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-accent-green" aria-hidden />
      ) : tone === "error" ? (
        <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-accent-red" aria-hidden />
      ) : null}
      <span className="break-words">{text}</span>
    </div>
  );
}
