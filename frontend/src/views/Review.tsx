import { useEffect, useState } from "react";
import Card from "../components/Card";
import PillBadge from "../components/PillBadge";
import ModelViewer from "../components/ModelViewer";
import { api, type ReviewData } from "../api";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; data: ReviewData };

export default function Review({ runPath }: { runPath: string | null }) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    api
      .getReview(runPath)
      .then((data) => {
        if (cancelled) return;
        if (!data)
          setState({
            kind: "error",
            message: runPath
              ? `No review data for ${runPath}.`
              : "No completed run available.",
          });
        else setState({ kind: "ok", data });
      })
      .catch((err) => {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        setState({ kind: "error", message: `Failed to load review: ${msg}` });
      });
    return () => {
      cancelled = true;
    };
  }, [runPath]);

  if (state.kind === "loading") {
    return (
      <div className="grid h-full place-items-center text-[13px] text-muted">
        Loading review…
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <div className="grid h-full place-items-center">
        <Card className="max-w-md text-center">
          <PillBadge tone="red">Not available</PillBadge>
          <p className="mt-3 text-[13.5px] text-muted">{state.message}</p>
        </Card>
      </div>
    );
  }

  const { data } = state;
  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-4 lg:grid-cols-[380px_minmax(0,1fr)]">
      <aside className="flex min-h-0 flex-col gap-4 overflow-hidden">
        <Card>
          <div className="flex items-center justify-between gap-2">
            <PillBadge tone="purple">Asset</PillBadge>
            <PillBadge tone={data.qa_passed ? "green" : "red"}>
              {data.qa_passed ? "QA Passed" : "Needs review"}
            </PillBadge>
          </div>
          <h2 className="mt-3 font-display text-xl font-semibold tracking-tight text-balance">
            {data.asset_id}
          </h2>
          <p className="mt-1 break-all font-mono text-[11px] text-muted-2">
            {data.glb_url}
          </p>
        </Card>

        <Card padded={false} className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex items-center justify-between px-5 pt-4">
            <PillBadge tone="blue">Concept</PillBadge>
            <span className="text-[11px] font-medium text-muted-2">1024×1024</span>
          </div>
          <div className="relative mx-5 mb-5 mt-3 flex-1 overflow-hidden rounded-xl border border-line bg-surface">
            <img
              src={data.concept_image_url}
              alt={`Concept for ${data.asset_id}`}
              className="absolute inset-0 h-full w-full object-contain"
            />
          </div>
        </Card>

        <Card>
          <PillBadge tone={data.warnings.length ? "amber" : "green"}>
            Warnings · {data.warnings.length}
          </PillBadge>
          {data.warnings.length === 0 ? (
            <p className="mt-2.5 text-[13px] text-muted">No warnings reported.</p>
          ) : (
            <ul className="mt-2.5 space-y-1.5 scrollbar-thin max-h-32 overflow-y-auto pr-1 text-[13px] text-ink">
              {data.warnings.map((w, i) => (
                <li key={i} className="flex gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-amber" />
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <PillBadge tone="neutral">Review</PillBadge>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <button
              type="button"
              className="h-8 rounded-lg bg-ink px-3 text-[13px] font-medium text-paper hover:opacity-90"
            >
              Approve
            </button>
            <button
              type="button"
              className="h-8 rounded-lg border border-line bg-card px-3 text-[13px] font-medium text-ink hover:border-accent-amber hover:text-accent-amber"
            >
              Needs changes
            </button>
            <button
              type="button"
              className="h-8 rounded-lg border border-line bg-card px-3 text-[13px] font-medium text-ink hover:border-accent-red hover:text-accent-red"
            >
              Reject
            </button>
          </div>
        </Card>
      </aside>

      <Card padded={false} className="relative flex min-h-0 flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 pt-4">
          <div className="flex items-center gap-2.5">
            <PillBadge tone="green">3D Preview</PillBadge>
            <span className="text-[11px] font-medium text-muted-2">WebGL · GLB</span>
          </div>
          <span className="text-[11px] font-medium text-muted-2">
            drag · scroll · right-click pan
          </span>
        </div>
        <ModelViewer initialUrl={data.glb_url} className="m-5 flex-1" />
      </Card>
    </div>
  );
}
