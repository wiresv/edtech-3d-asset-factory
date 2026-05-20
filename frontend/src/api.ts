export interface InitialRun {
  prompt: string;
  image_url: string;
  glb_url: string;
}

export interface ReviewData {
  asset_id: string;
  concept_image_url: string;
  glb_url: string;
  thumbnail_url: string;
  qa_passed: boolean;
  warnings: string[];
}

export interface ImageResponse {
  run_id: string;
  image_url: string;
}

export interface Run3dResponse {
  glb_url: string;
}

export interface SeedPrompt {
  id: string;
  label: string;
  subject: "biology" | "physics" | "earth_science";
  style: "conceptual" | "realistic";
  prompt: string;
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = (await r.json().catch(() => ({}))) as { error?: string } & T;
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

async function getJSON<T>(url: string): Promise<T | null> {
  const r = await fetch(url);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(r.statusText);
  const data = await r.json();
  return data as T | null;
}

export const api = {
  getInitial: () => getJSON<InitialRun>("/api/initial"),
  getSeedPrompts: () => getJSON<SeedPrompt[]>("/api/seed-prompts"),
  getReview: (run?: string | null) =>
    getJSON<ReviewData>("/api/review" + (run ? `?run=${encodeURIComponent(run)}` : "")),
  postImage: (prompt: string) =>
    postJSON<ImageResponse>("/api/image", { prompt }),
  postRun3d: (run_id: string) =>
    postJSON<Run3dResponse>("/api/run3d", { run_id }),
};
