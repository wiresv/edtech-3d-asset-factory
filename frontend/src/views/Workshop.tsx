import { useEffect, useRef, useState } from "react";
import Card from "../components/Card";
import PillBadge from "../components/PillBadge";
import StatusLine, { type StatusTone } from "../components/StatusLine";
import ModelViewer, { type ModelViewerHandle } from "../components/ModelViewer";
import { api, type SeedPrompt } from "../api";

const SUBJECT_DOT: Record<SeedPrompt["subject"], string> = {
  biology: "bg-accent-green",
  physics: "bg-accent-blue",
  earth_science: "bg-accent-amber",
};

interface State {
  prompt: string;
  imageUrl: string | null;
  currentRunId: string | null;
  initialGlbUrl: string | null;
  busy: "none" | "image" | "model";
  status: { text: string; tone: StatusTone };
}

const initialState: State = {
  prompt: "",
  imageUrl: null,
  currentRunId: null,
  initialGlbUrl: null,
  busy: "none",
  status: { text: "", tone: "idle" },
};

export default function Workshop() {
  const [s, setS] = useState<State>(initialState);
  const [seeds, setSeeds] = useState<SeedPrompt[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const viewerRef = useRef<ModelViewerHandle>(null);

  useEffect(() => {
    if (s.busy === "none") {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const handle = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 500);
    return () => window.clearInterval(handle);
  }, [s.busy]);

  useEffect(() => {
    let cancelled = false;
    api
      .getInitial()
      .then((r) => {
        if (cancelled || !r) return;
        setS((p) => ({
          ...p,
          prompt: r.prompt,
          imageUrl: r.image_url,
          initialGlbUrl: r.glb_url,
        }));
      })
      .catch(() => {});
    api
      .getSeedPrompts()
      .then((rows) => {
        if (cancelled || !rows) return;
        setSeeds(rows);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  async function onGenerateImage() {
    const prompt = s.prompt.trim();
    if (!prompt) {
      setS((p) => ({ ...p, status: { text: "Enter a prompt first.", tone: "error" } }));
      return;
    }
    setS((p) => ({
      ...p,
      busy: "image",
      status: { text: "Generating image with OpenAI — usually 10–30s…", tone: "busy" },
    }));
    try {
      const { run_id, image_url } = await api.postImage(prompt);
      setS((p) => ({
        ...p,
        busy: "none",
        currentRunId: run_id,
        imageUrl: image_url + "?t=" + Date.now(),
        status: { text: "Image ready. Approve to build the 3D model.", tone: "ok" },
      }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setS((p) => ({
        ...p,
        busy: "none",
        status: { text: `Image failed: ${msg}`, tone: "error" },
      }));
    }
  }

  async function onApprove() {
    if (!s.currentRunId) return;
    setS((p) => ({
      ...p,
      busy: "model",
      status: { text: "Running TRELLIS on the GPU — usually 1–2 min…", tone: "busy" },
    }));
    try {
      const { glb_url } = await api.postRun3d(s.currentRunId);
      await viewerRef.current?.load(glb_url);
      setS((p) => ({ ...p, busy: "none", status: { text: "Done.", tone: "ok" } }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setS((p) => ({
        ...p,
        busy: "none",
        status: { text: `3D failed: ${msg}`, tone: "error" },
      }));
    }
  }

  const imageReady = !!s.currentRunId || !!s.imageUrl;
  const genDisabled = s.busy !== "none";
  const approveDisabled = !s.currentRunId || s.busy !== "none";

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-4 lg:grid-cols-[380px_minmax(0,1fr)]">
      <aside className="flex min-h-0 flex-col gap-4 overflow-hidden">
        <Card className="flex min-h-0 flex-1 flex-col">
          <div className="flex items-center justify-between">
            <PillBadge tone="purple" icon={<Sparkles />}>
              Prompt
            </PillBadge>
            <KeyHint label="⌘ ↵" />
          </div>
          <textarea
            value={s.prompt}
            onChange={(e) => setS((p) => ({ ...p, prompt: e.target.value }))}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && !genDisabled) {
                e.preventDefault();
                onGenerateImage();
              }
            }}
            placeholder="A stylized chloroplast with prominent thylakoid stacks, soft conceptual shading…"
            className="mt-3 min-h-[110px] w-full flex-1 resize-none rounded-xl border border-line bg-paper px-3.5 py-3 text-[13.5px] leading-relaxed text-ink placeholder:text-muted-2 focus:border-ink focus:outline-none focus:ring-0"
          />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={onGenerateImage}
              disabled={genDisabled}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-ink px-3 text-[13px] font-medium text-paper transition-opacity hover:opacity-90 disabled:cursor-wait disabled:opacity-50"
            >
              {s.busy === "image" ? <Spinner /> : <Sparkles />}
              {s.busy === "image" ? "Generating" : "Generate image"}
            </button>
            <button
              type="button"
              onClick={onApprove}
              disabled={approveDisabled}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-line bg-card px-3 text-[13px] font-medium text-ink transition-colors hover:border-ink disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-line"
            >
              {s.busy === "model" ? <Spinner /> : <CubeIcon />}
              {s.busy === "model" ? "Building" : "Build 3D"}
            </button>
          </div>
          {seeds.length > 0 && (
            <div className="mt-4 border-t border-line-2 pt-3">
              <div className="mb-2 flex items-baseline justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-2">
                  Try one
                </span>
                <span className="text-[10px] text-muted-2">{seeds.length} examples</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {seeds.map((seed) => (
                  <button
                    key={seed.id}
                    type="button"
                    onClick={() => setS((p) => ({ ...p, prompt: seed.prompt }))}
                    disabled={genDisabled}
                    title={seed.label}
                    className="group inline-flex items-center gap-1.5 rounded-pill border border-line bg-card px-2.5 py-1 text-[11.5px] font-medium text-muted transition-all hover:border-ink hover:bg-surface hover:text-ink hover:shadow-card disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-line disabled:hover:bg-card disabled:hover:text-muted disabled:hover:shadow-none"
                  >
                    <span
                      className={
                        "h-1.5 w-1.5 rounded-full transition-transform group-hover:scale-125 " +
                        SUBJECT_DOT[seed.subject]
                      }
                    />
                    {seed.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="mt-2.5">
            <StatusLine
              text={
                s.busy !== "none" && elapsed > 0
                  ? `${s.status.text} (${elapsed}s)`
                  : s.status.text
              }
              tone={s.status.tone}
            />
          </div>
        </Card>

        <Card padded={false} className="flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-5 pt-4">
            <PillBadge tone="blue" icon={<ImageIcon />}>
              Concept
            </PillBadge>
            {s.imageUrl && (
              <span className="text-[11px] font-medium text-muted-2">1024×1024</span>
            )}
          </div>
          <div className="relative mx-5 mb-5 mt-3 aspect-square overflow-hidden rounded-xl border border-line bg-surface">
            {imageReady && s.imageUrl ? (
              <img
                src={s.imageUrl}
                alt="Concept preview"
                className="absolute inset-0 h-full w-full object-contain"
              />
            ) : (
              <div className="absolute inset-0 grid place-items-center text-[12px] text-muted-2">
                Submit a prompt to generate a concept.
              </div>
            )}
          </div>
        </Card>
      </aside>

      <Card padded={false} className="relative flex min-h-0 flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 pt-4">
          <div className="flex items-center gap-2.5">
            <PillBadge tone="green" icon={<CubeIcon />}>
              3D Preview
            </PillBadge>
            <span className="text-[11px] font-medium text-muted-2">WebGL · GLB</span>
          </div>
          <span className="text-[11px] font-medium text-muted-2">
            drag · scroll · right-click pan
          </span>
        </div>
        <ModelViewer
          ref={viewerRef}
          initialUrl={s.initialGlbUrl}
          placeholder="Submit a prompt to begin."
          className="m-5 flex-1"
        />
      </Card>
    </div>
  );
}

function KeyHint({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center rounded-md border border-line bg-surface px-1.5 py-0.5 font-mono text-[10.5px] font-medium text-muted">
      {label}
    </span>
  );
}

function Spinner() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden className="animate-spin">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.25" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function Sparkles() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 3l1.6 4.6L18 9l-4.4 1.4L12 15l-1.6-4.6L6 9l4.4-1.4L12 3zm7 9l.9 2.4L22 15l-2.1.6L19 18l-.9-2.4L16 15l2.1-.6L19 12z"
        fill="currentColor"
      />
    </svg>
  );
}

function ImageIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="3" y="5" width="18" height="14" rx="3" stroke="currentColor" strokeWidth="2" />
      <circle cx="9" cy="11" r="1.6" fill="currentColor" />
      <path d="M5 17l5-4 4 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function CubeIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 3l8 4.5v9L12 21 4 16.5v-9L12 3zM12 13l-6-3.5M12 13l6-3.5M12 13v8"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
