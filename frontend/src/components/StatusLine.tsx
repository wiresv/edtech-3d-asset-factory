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
    tone === "error" ? "text-accent-red"
    : tone === "ok" ? "text-accent-green"
    : tone === "busy" ? "text-ink-2"
    : "text-muted";
  return (
    <div className={`flex items-center gap-2 text-[13px] ${color}`}>
      {tone === "busy" && (
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-purple/40" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-purple" />
        </span>
      )}
      <span className="break-words leading-tight">{text}</span>
    </div>
  );
}
