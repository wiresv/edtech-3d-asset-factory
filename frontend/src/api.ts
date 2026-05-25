export interface InitialRun {
  prompt: string;
  image_url: string;
  glb_url: string;
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
  subject: "biology" | "chemistry" | "physics" | "earth_science" | "astronomy";
  style: "conceptual" | "realistic";
  prompt: string;
  cached: boolean;
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = (await r.json().catch(() => ({}))) as { error?: string } & T;
  if (!r.ok) throw new Error(data.error || r.statusText || `HTTP ${r.status}`);
  return data;
}

async function streamRun3d(
  run_id: string,
  fast: boolean,
  signal?: AbortSignal,
): Promise<Run3dResponse> {
  const r = await fetch("/api/run3d", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id, fast }),
    signal,
  });
  if (!r.ok || !r.body) {
    throw new Error(`HTTP ${r.status}${r.statusText ? " " + r.statusText : ""}`);
  }
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let final: { status?: string; glb_url?: string; error?: string } | null = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (value) buf += decoder.decode(value, { stream: true });
    let nl = buf.indexOf("\n");
    while (nl >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (line) {
        try {
          const obj = JSON.parse(line) as { status?: string; glb_url?: string; error?: string };
          if (obj.error || obj.status === "done") final = obj;
        } catch {
          // ignore non-JSON heartbeat noise
        }
      }
      nl = buf.indexOf("\n");
    }
    if (done) break;
  }
  if (!final) throw new Error("server closed connection without result");
  if (final.error) throw new Error(final.error);
  if (!final.glb_url) throw new Error("server reported done but returned no glb_url");
  return { glb_url: final.glb_url };
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
  getSeedImage: (id: string) =>
    getJSON<ImageResponse>("/api/seed-image?id=" + encodeURIComponent(id)),
  postImage: (prompt: string) =>
    postJSON<ImageResponse>("/api/image", { prompt }),
  postRun3d: (run_id: string, fast: boolean, signal?: AbortSignal) =>
    streamRun3d(run_id, fast, signal),
};
