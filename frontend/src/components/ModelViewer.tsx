import { useEffect, useImperativeHandle, useRef, useState, forwardRef } from "react";
import { useThreeViewer } from "../hooks/useThreeViewer";

export interface ModelViewerHandle {
  load: (url: string) => Promise<void>;
}

interface Props {
  initialUrl?: string | null;
  placeholder?: string;
  className?: string;
}

const ModelViewer = forwardRef<ModelViewerHandle, Props>(function ModelViewer(
  { initialUrl, placeholder = "Awaiting model", className = "" },
  ref,
) {
  const { containerRef, loadGlb } = useThreeViewer();
  const spotRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<{ text: string; tone: "info" | "error" | "hidden" }>({
    text: placeholder,
    tone: "info",
  });

  useImperativeHandle(
    ref,
    () => ({
      load: async (url: string) => {
        setStatus({ text: "Loading GLB…", tone: "info" });
        try {
          await loadGlb(url);
          setStatus({ text: "", tone: "hidden" });
        } catch (err) {
          setStatus({
            text: err instanceof Error ? `GLB failed: ${err.message}` : "GLB failed to load",
            tone: "error",
          });
        }
      },
    }),
    [loadGlb],
  );

  useEffect(() => {
    if (!initialUrl) return;
    let cancelled = false;
    setStatus({ text: "Loading GLB…", tone: "info" });
    loadGlb(initialUrl)
      .then(() => {
        if (!cancelled) setStatus({ text: "", tone: "hidden" });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : "GLB failed to load";
        setStatus({ text: `GLB failed: ${msg}`, tone: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [initialUrl, loadGlb]);

  function onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    const el = spotRef.current;
    if (!el) return;
    const r = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * 100;
    const y = ((e.clientY - r.top) / r.height) * 100;
    el.style.background = `radial-gradient(340px circle at ${x}% ${y}%, rgba(226,230,238,0.08), transparent 60%)`;
  }

  function onPointerLeave() {
    const el = spotRef.current;
    if (el) {
      el.style.background =
        "radial-gradient(340px circle at 50% 34%, rgba(226,230,238,0.04), transparent 60%)";
    }
  }

  return (
    <div
      className={`relative overflow-hidden rounded-card ring-1 ring-white/[0.06] ${className}`}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
    >
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(125% 95% at 50% -6%, #1a1b22 0%, #101117 52%, #08080c 100%)",
        }}
      />
      <div ref={spotRef} className="pointer-events-none absolute inset-0" />
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-2/5"
        style={{
          background:
            "radial-gradient(56% 50% at 50% 116%, rgba(150,160,185,0.14) 0%, transparent 70%)",
        }}
      />
      <div ref={containerRef} className="relative h-full w-full" />
      {status.tone !== "hidden" && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <span
            className={
              "rounded-pill border px-3 py-1.5 text-[12px] font-medium backdrop-blur-md " +
              (status.tone === "error"
                ? "border-accent-red/40 bg-accent-red/20 text-white"
                : "border-white/10 bg-white/10 text-white/80")
            }
          >
            {status.text}
          </span>
        </div>
      )}
    </div>
  );
});

export default ModelViewer;
