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
    <div className={`relative overflow-hidden rounded-card ${className}`}>
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 90% at 30% 20%, #1a1a20 0%, #0a0a0c 60%, #050507 100%)",
        }}
      />
      <div ref={containerRef} className="relative h-full w-full" />
      {status.tone !== "hidden" && (
        <div
          className={
            "pointer-events-none absolute inset-x-5 bottom-5 text-[12px] font-medium " +
            (status.tone === "error" ? "text-accent-red" : "text-white/70")
          }
        >
          {status.text}
        </div>
      )}
    </div>
  );
});

export default ModelViewer;
