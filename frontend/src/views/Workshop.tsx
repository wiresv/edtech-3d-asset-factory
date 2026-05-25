import { type ReactNode, useEffect, useRef, useState } from "react";
import Card from "../components/Card";
import StatusLine, { type StatusTone } from "../components/StatusLine";
import ModelViewer, { type ModelViewerHandle } from "../components/ModelViewer";
import { api, type SeedPrompt } from "../api";

const SUBJECT_DOT: Record<SeedPrompt["subject"], string> = {
  biology: "bg-accent-green",
  physics: "bg-accent-blue",
  earth_science: "bg-accent-amber",
};

type StepState = "pending" | "active" | "done";

interface State {
  prompt: string;
  imageUrl: string | null;
  currentRunId: string | null;
  initialGlbUrl: string | null;
  modelReady: boolean;
  busy: "none" | "image" | "model";
  status: { text: string; tone: StatusTone };
  fast: boolean;
}

const initialState: State = {
  prompt: "",
  imageUrl: null,
  currentRunId: null,
  initialGlbUrl: null,
  modelReady: false,
  busy: "none",
  status: { text: "", tone: "idle" },
  fast: false,
};

export default function Workshop() {
  const [s, setS] = useState<State>(initialState);
  const [seeds, setSeeds] = useState<SeedPrompt[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [conceptOpen, setConceptOpen] = useState(false);
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
          modelReady: true,
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

  useEffect(() => {
    if (!conceptOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setConceptOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [conceptOpen]);

  async function onGenerateImage() {
    const prompt = s.prompt.trim();
    if (!prompt) {
      setS((p) => ({ ...p, status: { text: "Enter a prompt first.", tone: "error" } }));
      return;
    }
    setS((p) => ({
      ...p,
      busy: "image",
      status: { text: "Generating image with OpenAI — usually 15–30s…", tone: "busy" },
    }));
    try {
      const { run_id, image_url } = await api.postImage(prompt);
      setS((p) => ({
        ...p,
        busy: "none",
        currentRunId: run_id,
        imageUrl: image_url + "?t=" + Date.now(),
        modelReady: false,
        status: { text: "Concept ready. Build the 3D model when you're happy with it.", tone: "ok" },
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

  async function onSeedClick(seed: SeedPrompt) {
    setS((p) => ({
      ...p,
      prompt: seed.prompt,
      busy: "image",
      status: { text: "Loading cached concept…", tone: "busy" },
    }));
    const r = await api.getSeedImage(seed.id).catch(() => null);
    if (r) {
      setS((p) => ({
        ...p,
        busy: "none",
        currentRunId: r.run_id,
        imageUrl: r.image_url + "?t=" + Date.now(),
        modelReady: false,
        status: { text: "Cached concept ready. Build the 3D model to continue.", tone: "ok" },
      }));
      return;
    }
    setS((p) => ({
      ...p,
      busy: "none",
      status: { text: "Prompt loaded. Click Generate image.", tone: "idle" },
    }));
  }

  async function onApprove() {
    if (!s.currentRunId) return;
    const fast = s.fast;
    setS((p) => ({
      ...p,
      busy: "model",
      status: {
        text: fast
          ? "Running TRELLIS (draft preset) on the GPU — usually under a minute…"
          : "Running TRELLIS (quality preset) on the GPU — usually 1–2 min…",
        tone: "busy",
      },
    }));
    try {
      const { glb_url } = await api.postRun3d(s.currentRunId, fast);
      await viewerRef.current?.load(glb_url);
      setS((p) => ({
        ...p,
        busy: "none",
        modelReady: true,
        status: { text: "Model ready.", tone: "ok" },
      }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setS((p) => ({
        ...p,
        busy: "none",
        status: { text: `3D failed: ${msg}`, tone: "error" },
      }));
    }
  }

  const genDisabled = s.busy !== "none";
  const approveDisabled = !s.currentRunId || s.busy !== "none";
  const conceptInteractive = !!s.imageUrl && s.busy !== "image";
  const statusText =
    s.busy !== "none" && elapsed > 0 ? `${s.status.text} (${elapsed}s)` : s.status.text;
  const elapsedLabel = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`;

  const conceptActive = s.busy === "image";
  const modelActive = s.busy === "model";
  const promptState: StepState = s.imageUrl || conceptActive ? "done" : "active";
  const conceptState: StepState = conceptActive
    ? "active"
    : s.imageUrl
      ? "done"
      : "pending";
  const modelState: StepState = modelActive ? "active" : s.modelReady ? "done" : "pending";

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex shrink-0 animate-riseIn items-center justify-center gap-2 rounded-card border border-line bg-card/70 px-4 py-2 shadow-card backdrop-blur-md">
        <StepNode icon={<Sparkles />} label="Prompt" state={promptState} />
        <Connector state={conceptState === "pending" ? "idle" : conceptState} />
        <StepNode icon={<ImageIcon />} label="Concept" state={conceptState} />
        <Connector state={modelState === "pending" ? "idle" : modelState} />
        <StepNode icon={<CubeIcon />} label="Model" state={modelState} />
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[clamp(340px,26vw,400px)_minmax(0,1fr)]">
        <aside className="flex min-h-0 animate-riseIn" style={{ animationDelay: "60ms" }}>
          <Card className="flex min-h-0 w-full flex-col overflow-hidden">
            <span className="block text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-2">
              Describe your asset
            </span>

            <textarea
              value={s.prompt}
              onChange={(e) => setS((p) => ({ ...p, prompt: e.target.value }))}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && !genDisabled) {
                  e.preventDefault();
                  onGenerateImage();
                }
              }}
              placeholder="A stylized chloroplast with prominent thylakoid stacks, soft conceptual shading, clean educational form…"
              className="mt-2.5 h-36 w-full resize-none rounded-xl border border-line bg-paper px-3.5 py-3 text-[13.5px] leading-relaxed text-ink outline-none transition placeholder:text-muted-2 focus:border-accent/50 focus:ring-4 focus:ring-accent/10"
            />

            <div className="mt-3 flex items-center gap-2">
              <button
                type="button"
                onClick={onGenerateImage}
                disabled={genDisabled}
                className="group inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-lg bg-ink px-3 text-[13px] font-medium text-white shadow-[0_1px_2px_0_rgb(16_17_26/0.06),inset_0_1px_0_0_rgb(255_255_255/0.1)] outline-none transition hover:bg-[#1c1c22] active:scale-[0.985] focus-visible:ring-2 focus-visible:ring-ink/25 disabled:cursor-wait disabled:opacity-60 disabled:active:scale-100"
              >
                <span className="transition-transform duration-300 group-hover:rotate-[16deg] group-hover:scale-110">
                  {s.busy === "image" ? <Spinner /> : <Sparkles />}
                </span>
                <span>{s.busy === "image" ? "Generating" : "Generate image"}</span>
                {s.busy !== "image" && (
                  <kbd className="ml-0.5 hidden rounded border border-white/15 bg-white/10 px-1 py-px font-mono text-[10px] font-medium leading-none text-white/55 sm:inline-block">
                    ⌘↵
                  </kbd>
                )}
              </button>
              <button
                type="button"
                onClick={onApprove}
                disabled={approveDisabled}
                className="inline-flex h-9 items-center justify-center gap-1.5 rounded-lg border border-line bg-card px-3.5 text-[13px] font-medium text-ink outline-none transition hover:border-accent/30 hover:bg-surface active:scale-[0.985] focus-visible:ring-2 focus-visible:ring-accent/40 disabled:cursor-not-allowed disabled:opacity-45 disabled:active:scale-100 disabled:hover:border-line disabled:hover:bg-card"
              >
                {s.busy === "model" ? <Spinner /> : <CubeIcon />}
                {s.busy === "model" ? "Building" : "Build 3D"}
              </button>
            </div>

            <div
              role="radiogroup"
              aria-label="3D generation quality preset"
              className="mt-2.5 inline-flex w-full items-center gap-0.5 rounded-lg border border-line bg-surface p-0.5 text-[12px] font-medium"
            >
              <button
                type="button"
                role="radio"
                aria-checked={!s.fast}
                onClick={() => setS((p) => ({ ...p, fast: false }))}
                disabled={s.busy !== "none"}
                title="Full quality — sharper mesh and texture, ~1–2 min"
                className={
                  "inline-flex h-7 flex-1 items-center justify-center gap-1.5 rounded-md transition disabled:cursor-not-allowed disabled:opacity-50 " +
                  (!s.fast ? "bg-card text-ink shadow-card" : "text-muted hover:text-ink")
                }
              >
                <DiamondIcon />
                Quality
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={s.fast}
                onClick={() => setS((p) => ({ ...p, fast: true }))}
                disabled={s.busy !== "none"}
                title="Draft — faster but visibly rougher; coarser mesh, lower-res texture"
                className={
                  "inline-flex h-7 flex-1 items-center justify-center gap-1.5 rounded-md transition disabled:cursor-not-allowed disabled:opacity-50 " +
                  (s.fast ? "bg-card text-accent-amber shadow-card" : "text-muted hover:text-ink")
                }
              >
                <BoltIcon />
                Draft
              </button>
            </div>

            <p className="mt-1.5 text-[11px] leading-snug text-muted-2">
              {s.fast
                ? "Draft · faster generation, lower-fidelity mesh + texture."
                : "Quality · sharper mesh + texture, longer wait."}
            </p>

            <div className="mt-2 min-h-[34px]">
              <StatusLine text={statusText} tone={s.status.tone} />
            </div>

            {seeds.length === 0 && <div className="flex-1" />}
            {seeds.length > 0 && (
              <div className="mt-3 flex min-h-0 flex-1 flex-col border-t border-line-2 pt-3">
                <div className="mb-2.5 flex items-baseline justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-2">
                    Examples
                  </span>
                  <span className="font-mono text-[10px] text-muted-2">{seeds.length} ready</span>
                </div>
                <div className="-mr-1 flex min-h-0 flex-1 flex-wrap content-start gap-1.5 overflow-y-auto pr-1 scrollbar-thin">
                  {seeds.map((seed) => (
                    <button
                      key={seed.id}
                      type="button"
                      onClick={() => onSeedClick(seed)}
                      disabled={genDisabled}
                      title={seed.cached ? `${seed.label} — cached, instant` : seed.label}
                      className="group inline-flex items-center gap-1.5 rounded-pill border border-line bg-card px-2.5 py-[5px] text-[11.5px] font-medium text-ink-2 transition-all hover:-translate-y-px hover:border-accent/40 hover:bg-surface hover:text-ink hover:shadow-card active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:border-line disabled:hover:bg-card disabled:hover:text-ink-2 disabled:hover:shadow-none"
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
          </Card>
        </aside>

        <div className="flex min-h-0 animate-riseIn" style={{ animationDelay: "120ms" }}>
          <Card padded={false} className="relative flex min-h-0 w-full flex-col overflow-hidden">
            <div className="flex items-center justify-between px-5 pt-4">
              <span className="font-mono text-[11px] font-medium tracking-tight text-muted-2">
                WebGL · GLB
              </span>
              <span className="hidden font-mono text-[11px] text-muted-2 sm:inline">
                drag · scroll · right-click pan
              </span>
            </div>

            <ModelViewer
              ref={viewerRef}
              initialUrl={s.initialGlbUrl}
              placeholder="Generate a concept, then build the 3D model."
              className="m-4 mt-3 flex-1"
            />

            {s.busy === "model" && (
              <div className="pointer-events-none absolute inset-0 z-20 grid animate-fadeIn place-items-center">
                <div className="flex flex-col items-center gap-3 rounded-2xl border border-white/10 bg-ink/40 px-8 py-7 shadow-pop backdrop-blur-xl">
                  <div className="relative grid h-14 w-14 place-items-center text-accent">
                    <span className="absolute inset-0 animate-breathe rounded-full bg-accent/20 blur-md" />
                    <span className="absolute inset-0 animate-spinSlow rounded-full border-2 border-white/10 border-t-accent" />
                    <span className="relative [&_svg]:h-6 [&_svg]:w-6">
                      <CubeIcon />
                    </span>
                  </div>
                  <div className="text-center">
                    <div className="text-[13px] font-semibold text-white">Forging model</div>
                    <div className="font-mono text-[11px] text-white/55">
                      {s.fast ? "draft preset" : "quality preset"}
                    </div>
                  </div>
                  <div className="font-mono text-[24px] font-semibold tabular-nums text-white">
                    {elapsedLabel}
                  </div>
                </div>
              </div>
            )}

            <div
              className={
                "absolute bottom-4 right-4 z-10 w-[clamp(124px,15vw,184px)] " +
                (conceptInteractive ? "" : "pointer-events-none")
              }
            >
              <button
                type="button"
                onClick={() => conceptInteractive && setConceptOpen(true)}
                disabled={!conceptInteractive}
                className="group relative block aspect-square w-full overflow-hidden rounded-xl border border-white/15 bg-card shadow-pop ring-1 ring-white/10 transition-transform duration-200 enabled:hover:-translate-y-0.5 disabled:cursor-default"
              >
                <span className="absolute left-2 top-2 z-10 inline-flex items-center gap-1 rounded-pill bg-card/85 px-1.5 py-0.5 text-[9.5px] font-semibold uppercase tracking-[0.07em] text-muted backdrop-blur-sm">
                  <ImageIcon />
                  Concept
                </span>
                {s.imageUrl ? (
                  <>
                    <img
                      key={s.imageUrl}
                      src={s.imageUrl}
                      alt="Concept preview"
                      className="absolute inset-0 h-full w-full animate-revealIn bg-surface object-contain"
                    />
                    {s.busy !== "image" && (
                      <span className="absolute bottom-2 right-2 z-10 inline-flex items-center gap-1 rounded-pill bg-ink/70 px-1.5 py-0.5 text-[9.5px] font-medium text-white opacity-0 backdrop-blur-sm transition-opacity group-hover:opacity-100">
                        <ExpandIcon />
                        Expand
                      </span>
                    )}
                  </>
                ) : (
                  <span className="absolute inset-0 grid place-items-center px-4 text-center text-[10.5px] leading-tight text-muted-2">
                    Concept appears here
                  </span>
                )}
                {s.busy === "image" && (
                  <span className="absolute inset-0 z-10 grid place-items-center overflow-hidden bg-card/70 backdrop-blur-sm">
                    <span className="absolute inset-y-0 w-1/2 animate-shimmer bg-gradient-to-r from-transparent via-accent/20 to-transparent" />
                    <span className="relative inline-flex items-center gap-1.5 text-[11px] font-medium text-muted">
                      <Spinner />
                      Generating…
                    </span>
                  </span>
                )}
              </button>
            </div>
          </Card>
        </div>
      </div>

      {conceptOpen && s.imageUrl && (
        <div
          className="fixed inset-0 z-50 grid animate-fadeIn place-items-center bg-ink/70 p-8 backdrop-blur-sm"
          onClick={() => setConceptOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Concept image"
        >
          <figure
            className="flex max-h-full max-w-full animate-popIn flex-col items-center gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={s.imageUrl}
              alt="Concept"
              className="max-h-[80vh] max-w-[80vw] rounded-card border border-white/10 bg-surface object-contain shadow-pop"
            />
            <figcaption className="flex items-center gap-2 text-[12px] font-medium text-white/70">
              <span className="font-mono">concept · 1024×1024</span>
              <span className="text-white/30">·</span>
              <kbd className="rounded border border-white/20 px-1.5 py-0.5 font-mono text-[10px] text-white/60">
                Esc
              </kbd>
              to close
            </figcaption>
          </figure>
        </div>
      )}
    </div>
  );
}

function StepNode({ icon, label, state }: { icon: ReactNode; label: string; state: StepState }) {
  const ring =
    state === "done"
      ? "border-accent bg-accent text-white"
      : state === "active"
        ? "scale-110 border-accent bg-accent/5 text-accent"
        : "border-line bg-card text-muted-2";
  return (
    <div className="flex items-center gap-2">
      <span
        className={
          "relative grid h-6 w-6 place-items-center rounded-full border transition-all duration-300 ease-out " +
          ring
        }
      >
        {state === "active" && (
          <span className="absolute inset-0 animate-ping rounded-full bg-accent/25" />
        )}
        <span className="relative">{state === "done" ? <CheckIcon /> : icon}</span>
      </span>
      <span
        className={
          "text-[12px] font-medium transition-colors " +
          (state === "pending" ? "text-muted-2" : "text-ink")
        }
      >
        {label}
      </span>
    </div>
  );
}

function Connector({ state }: { state: "idle" | "active" | "done" }) {
  return (
    <div className="relative mx-1.5 h-px w-10 overflow-hidden rounded-full bg-line sm:w-16">
      <div
        className={
          "absolute inset-y-0 left-0 rounded-full bg-accent transition-all duration-700 " +
          (state === "done" ? "w-full" : "w-0")
        }
      />
      {state === "active" && (
        <div className="absolute inset-y-0 w-1/3 animate-flow rounded-full bg-gradient-to-r from-transparent via-accent to-transparent" />
      )}
    </div>
  );
}

function Spinner() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden className="animate-spin">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
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

function BoltIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" />
    </svg>
  );
}

function DiamondIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 2l10 10-10 10L2 12z" />
    </svg>
  );
}

function ExpandIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M9 4H4v5M15 4h5v5M9 20H4v-5M15 20h5v-5"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M5 12.5l4.5 4.5L19 7"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        style={{ strokeDasharray: 1 }}
        className="animate-drawIn"
      />
    </svg>
  );
}
