import { useEffect, useImperativeHandle, useState, forwardRef } from "react";
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

  return (
    <div className={`relative overflow-hidden rounded-card ring-1 ring-line ${className}`}>
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(125% 95% at 50% -8%, #ffffff 0%, #f3f4f7 46%, #e7e9ee 100%)",
        }}
      />
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3"
        style={{
          background:
            "radial-gradient(60% 80% at 50% 120%, rgb(11 11 13 / 0.10) 0%, transparent 70%)",
        }}
      />
      <div ref={containerRef} className="relative h-full w-full" />
      {status.tone !== "hidden" && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <span
            className={
              "rounded-pill border px-3 py-1.5 text-[12px] font-medium backdrop-blur-sm " +
              (status.tone === "error"
                ? "border-accent-red/20 bg-accent-red/10 text-accent-red"
                : "border-line bg-card/80 text-muted")
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
