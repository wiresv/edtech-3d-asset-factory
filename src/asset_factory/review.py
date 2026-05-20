from __future__ import annotations

import html
import http.server
import json
from functools import partial
from pathlib import Path


class ReviewHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True


def _script_json(value: str) -> str:
    return (
        json.dumps(value)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def build_review_html(
    *,
    asset_id: str,
    concept_image: str,
    glb_path: str,
    thumbnail: str,
    qa_passed: bool,
    warnings: list[str],
) -> str:
    escaped_asset_id = html.escape(asset_id, quote=True)
    escaped_concept_image = html.escape(concept_image, quote=True)
    escaped_glb_path = html.escape(glb_path, quote=True)
    escaped_thumbnail = html.escape(thumbnail, quote=True)
    warning_items = "".join(f"<li>{html.escape(warning, quote=True)}</li>" for warning in warnings)
    if not warning_items:
        warning_items = "<li>No warnings reported.</li>"
    status_label = "Passed" if qa_passed else "Needs review"
    status_class = "passed" if qa_passed else "failed"
    glb_url = _script_json(f"../{glb_path}")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Review {escaped_asset_id}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #18212f;
      --muted: #5f6b7a;
      --line: #d8dee8;
      --paper: #ffffff;
      --canvas: #f4f6f8;
      --accent: #1b6b8f;
      --passed: #047857;
      --failed: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
      background: var(--canvas);
      color: var(--ink);
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 20px 28px;
      background: var(--paper);
      border-bottom: 1px solid var(--line);
    }}
    h1, h2, p {{ margin-top: 0; }}
    h1 {{ margin-bottom: 0; font-size: 1.35rem; }}
    h2 {{ font-size: 0.95rem; }}
    main {{
      display: grid;
      grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
      gap: 20px;
      padding: 20px;
    }}
    img {{
      display: block;
      width: 100%;
      border: 1px solid var(--line);
      background: white;
    }}
    ul {{ padding-left: 20px; color: var(--muted); }}
    button {{
      min-height: 36px;
      margin: 0 8px 8px 0;
      padding: 8px 12px;
      border: 1px solid #a9b4c2;
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      font: inherit;
    }}
    button.primary {{
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
    }}
    .panel {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .stack {{ display: grid; gap: 16px; }}
    .status {{
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.86rem;
      font-weight: 700;
    }}
    .status.passed {{ background: #dff7ea; color: var(--passed); }}
    .status.failed {{ background: #fde8e4; color: var(--failed); }}
    #viewer {{
      position: relative;
      min-height: 560px;
      background: #111827;
      border-radius: 8px;
      overflow: hidden;
    }}
    #viewer-status {{
      position: absolute;
      left: 16px;
      right: 16px;
      bottom: 16px;
      color: #f9fafb;
      font-size: 0.9rem;
    }}
    #viewer-status.error {{ color: #fecaca; }}
    .path {{
      overflow-wrap: anywhere;
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.86rem;
    }}
    @media (max-width: 800px) {{
      header {{ align-items: flex-start; flex-direction: column; }}
      main {{ grid-template-columns: 1fr; }}
      #viewer {{ min-height: 420px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{escaped_asset_id}</h1>
    <div class="status {status_class}">QA {status_label}</div>
  </header>
  <main>
    <aside class="stack">
      <section class="panel">
        <h2>Concept Image</h2>
        <img src="../{escaped_concept_image}" alt="Concept image for {escaped_asset_id}">
      </section>
      <section class="panel">
        <h2>Warnings</h2>
        <ul>{warning_items}</ul>
      </section>
      <section class="panel">
        <h2>Review</h2>
        <button class="primary" type="button">Approve</button>
        <button type="button">Needs changes</button>
        <button type="button">Reject</button>
      </section>
    </aside>
    <section class="panel">
      <h2>3D Preview</h2>
      <div id="viewer"><div id="viewer-status">Loading GLB...</div></div>
      <p class="path">GLB: {escaped_glb_path}</p>
      <p class="path">Thumbnail: {escaped_thumbnail}</p>
    </section>
  </main>
  <script type="importmap">
    {{
      "imports": {{
        "three": "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js",
        "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/"
      }}
    }}
  </script>
  <script type="module">
    import * as THREE from 'three';
    import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
    import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';

    const viewer = document.getElementById('viewer');
    const viewerStatus = document.getElementById('viewer-status');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111827);

    const camera = new THREE.PerspectiveCamera(
      45,
      viewer.clientWidth / viewer.clientHeight,
      0.1,
      100
    );
    camera.position.set(2.5, 2, 2.5);

    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(viewer.clientWidth, viewer.clientHeight);
    viewer.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x223344, 3));
    const keyLight = new THREE.DirectionalLight(0xffffff, 2);
    keyLight.position.set(3, 4, 2);
    scene.add(keyLight);

    function frameObject(object) {{
      const box = new THREE.Box3().setFromObject(object);
      const center = new THREE.Vector3();
      const size = new THREE.Vector3();
      box.getCenter(center);
      box.getSize(size);

      const maxSize = Math.max(size.x, size.y, size.z, 1);
      const fitDistance = maxSize / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));
      const viewDirection = new THREE.Vector3(1, 0.8, 1).normalize();

      camera.position.copy(center).add(viewDirection.multiplyScalar(fitDistance * 1.6));
      camera.near = Math.max(fitDistance / 100, 0.001);
      camera.far = Math.max(fitDistance * 100, maxSize * 10);
      camera.lookAt(center);
      camera.updateProjectionMatrix();

      controls.target.copy(center);
      controls.update();
    }}

    const loader = new GLTFLoader();
    loader.load({glb_url}, (gltf) => {{
      viewerStatus.hidden = true;
      scene.add(gltf.scene);
      frameObject(gltf.scene);
      renderer.setAnimationLoop(() => {{
        controls.update();
        renderer.render(scene, camera);
      }});
    }}, undefined, () => {{
      viewerStatus.textContent = 'GLB failed to load';
      viewerStatus.classList.add('error');
    }});

    window.addEventListener('resize', () => {{
      camera.aspect = viewer.clientWidth / viewer.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(viewer.clientWidth, viewer.clientHeight);
    }});
  </script>
</body>
</html>
"""


def write_review_html(
    run_dir: Path,
    *,
    asset_id: str,
    concept_image: str,
    glb_path: str,
    thumbnail: str,
    qa_passed: bool,
    warnings: list[str],
) -> Path:
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "review.html"
    path.write_text(
        build_review_html(
            asset_id=asset_id,
            concept_image=concept_image,
            glb_path=glb_path,
            thumbnail=thumbnail,
            qa_passed=qa_passed,
            warnings=warnings,
        ),
        encoding="utf-8",
    )
    return path


def serve_review(run_dir: Path, port: int) -> None:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=run_dir)
    with ReviewHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving review for {run_dir} at http://127.0.0.1:{port}/reports/review.html")
        httpd.serve_forever()


_WORKSHOP_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Asset Workshop</title>
  <style>
    :root { color-scheme: light; --ink:#18212f; --muted:#5f6b7a; --line:#d8dee8;
            --paper:#fff; --canvas:#f4f6f8; --accent:#1b6b8f; --err:#b42318; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: Inter, ui-sans-serif, system-ui, sans-serif;
           background: var(--canvas); color: var(--ink); }
    header { padding:20px 28px; background: var(--paper); border-bottom:1px solid var(--line); }
    h1 { margin:0; font-size:1.25rem; }
    h2 { font-size:0.95rem; margin-top:0; }
    main { display:grid; grid-template-columns: minmax(320px, 420px) minmax(0,1fr);
           gap:20px; padding:20px; }
    .panel { background:var(--paper); border:1px solid var(--line); border-radius:8px; padding:16px; }
    textarea { width:100%; min-height:140px; padding:10px; font:inherit;
               border:1px solid #a9b4c2; border-radius:6px; resize:vertical; }
    button { min-height:36px; margin:8px 8px 0 0; padding:8px 14px;
             border:1px solid #a9b4c2; border-radius:6px; background:#fff;
             color:var(--ink); font:inherit; cursor:pointer; }
    button.primary { border-color:var(--accent); background:var(--accent); color:#fff; }
    button:disabled { opacity:.5; cursor:wait; }
    #preview { width:100%; border:1px solid var(--line); background:#fff;
               display:block; min-height:240px; }
    #status { margin-top:10px; color:var(--muted); font-size:0.9rem;
              overflow-wrap:anywhere; }
    #status.err { color: var(--err); }
    #viewer { position:relative; min-height:520px; background:#111827;
              border-radius:8px; overflow:hidden; }
    #viewer-status { position:absolute; left:16px; right:16px; bottom:16px;
                     color:#f9fafb; font-size:0.9rem; }
    .hidden { display:none !important; }
  </style>
</head>
<body>
  <header><h1>Asset Workshop</h1></header>
  <main>
    <aside class="panel">
      <h2>Prompt</h2>
      <textarea id="prompt" placeholder="Describe the object to generate..."></textarea>
      <button id="gen-image" class="primary" type="button">Generate image</button>
      <button id="approve" type="button" disabled>Approve &amp; build 3D</button>
      <div id="status"></div>
      <h2 style="margin-top:16px">Concept image</h2>
      <img id="preview" alt="">
    </aside>
    <section class="panel">
      <h2>3D Preview</h2>
      <div id="viewer"><div id="viewer-status">Submit a prompt to begin.</div></div>
    </section>
  </main>
  <script type="importmap">
    {
      "imports": {
        "three": "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js",
        "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/"
      }
    }
  </script>
  <script type="module">
    import * as THREE from 'three';
    import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
    import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

    const $ = (id) => document.getElementById(id);
    const promptEl = $('prompt'), genBtn = $('gen-image'), approveBtn = $('approve');
    const statusEl = $('status'), preview = $('preview');
    const viewer = $('viewer'), viewerStatus = $('viewer-status');
    let currentRunId = null, sceneState = null;

    if (window.__INITIAL) {
      promptEl.value = window.__INITIAL.prompt;
      preview.src = window.__INITIAL.image_url;
      queueMicrotask(() => loadGlb(window.__INITIAL.glb_url));
    }

    function setStatus(msg, isErr=false) {
      statusEl.textContent = msg;
      statusEl.classList.toggle('err', isErr);
    }

    async function postJSON(url, body) {
      const r = await fetch(url, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || r.statusText);
      return data;
    }

    genBtn.addEventListener('click', async () => {
      const prompt = promptEl.value.trim();
      if (!prompt) { setStatus('Enter a prompt first.', true); return; }
      genBtn.disabled = true; approveBtn.disabled = true;
      setStatus('Generating image with OpenAI...');
      try {
        const { run_id, image_url } = await postJSON('/api/image', { prompt });
        currentRunId = run_id;
        preview.src = image_url + '?t=' + Date.now();
        approveBtn.disabled = false;
        setStatus('Image ready. Approve to build the 3D model.');
      } catch (e) { setStatus('Image failed: ' + e.message, true); }
      finally { genBtn.disabled = false; }
    });

    approveBtn.addEventListener('click', async () => {
      if (!currentRunId) return;
      approveBtn.disabled = true; genBtn.disabled = true;
      setStatus('Running TRELLIS — this takes about 2 minutes...');
      viewerStatus.textContent = 'Generating 3D...';
      try {
        const { glb_url } = await postJSON('/api/run3d', { run_id: currentRunId });
        setStatus('Done.');
        loadGlb(glb_url);
      } catch (e) {
        setStatus('3D failed: ' + e.message, true);
        viewerStatus.textContent = 'Generation failed.';
      } finally { approveBtn.disabled = false; genBtn.disabled = false; }
    });

    function initScene() {
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x111827);
      const camera = new THREE.PerspectiveCamera(45,
        viewer.clientWidth / viewer.clientHeight, 0.1, 100);
      camera.position.set(2.5, 2, 2.5);
      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setPixelRatio(window.devicePixelRatio);
      renderer.setSize(viewer.clientWidth, viewer.clientHeight);
      viewer.appendChild(renderer.domElement);
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      scene.add(new THREE.HemisphereLight(0xffffff, 0x223344, 3));
      const key = new THREE.DirectionalLight(0xffffff, 2);
      key.position.set(3, 4, 2);
      scene.add(key);
      window.addEventListener('resize', () => {
        camera.aspect = viewer.clientWidth / viewer.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(viewer.clientWidth, viewer.clientHeight);
      });
      return { scene, camera, renderer, controls };
    }

    function frame(object, s) {
      const box = new THREE.Box3().setFromObject(object);
      const center = new THREE.Vector3(), size = new THREE.Vector3();
      box.getCenter(center); box.getSize(size);
      const maxSize = Math.max(size.x, size.y, size.z, 1);
      const fit = maxSize / (2 * Math.tan(THREE.MathUtils.degToRad(s.camera.fov)/2));
      const dir = new THREE.Vector3(1, 0.8, 1).normalize();
      s.camera.position.copy(center).add(dir.multiplyScalar(fit * 1.6));
      s.camera.near = Math.max(fit / 100, 0.001);
      s.camera.far = Math.max(fit * 100, maxSize * 10);
      s.camera.lookAt(center); s.camera.updateProjectionMatrix();
      s.controls.target.copy(center); s.controls.update();
    }

    function loadGlb(url) {
      if (!sceneState) sceneState = initScene();
      while (sceneState.scene.children.length > 2) {
        sceneState.scene.remove(sceneState.scene.children[2]);
      }
      viewerStatus.textContent = 'Loading GLB...';
      new GLTFLoader().load(url, (gltf) => {
        viewerStatus.classList.add('hidden');
        sceneState.scene.add(gltf.scene);
        frame(gltf.scene, sceneState);
        sceneState.renderer.setAnimationLoop(() => {
          sceneState.controls.update();
          sceneState.renderer.render(sceneState.scene, sceneState.camera);
        });
      }, undefined, () => { viewerStatus.textContent = 'GLB failed to load.'; });
    }
  </script>
</body>
</html>
"""


def build_workshop_html(initial: dict | None = None) -> str:
    init_blob = _script_json(json.dumps(initial)) if initial else "null"
    return _WORKSHOP_HTML.replace(
        "</body>",
        f"<script>window.__INITIAL = JSON.parse({init_blob});</script></body>",
    )


def _find_initial_run(runs_root: Path) -> dict | None:
    """Pick the newest completed run under runs_root (excluding workshop/)."""
    if not runs_root.is_dir():
        return None
    candidates: list[tuple[float, Path, Path, Path, Path]] = []
    for asset_dir in runs_root.iterdir():
        if not asset_dir.is_dir() or asset_dir.name == "workshop":
            continue
        for run_dir in asset_dir.iterdir():
            if not run_dir.is_dir():
                continue
            prompt = run_dir / "image" / "prompt.txt"
            image = run_dir / "image" / "concept.png"
            glb = run_dir / "optimize" / "asset.glb"
            if not (prompt.exists() and image.exists() and glb.exists()):
                continue
            candidates.append((run_dir.stat().st_mtime, run_dir, prompt, image, glb))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    _, _, prompt, image, glb = candidates[0]
    rel = lambda p: "/" + p.relative_to(runs_root).as_posix()
    return {
        "prompt": prompt.read_text(encoding="utf-8"),
        "image_url": rel(image),
        "glb_url": rel(glb),
    }


class _WorkshopHandler(http.server.SimpleHTTPRequestHandler):
    runs_root: Path  # set by serve_workshop
    initial: dict | None = None

    def do_GET(self) -> None:
        if self.path in ("/", "/workshop", "/workshop.html"):
            body = build_workshop_html(self.initial).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/image":
                result = self._gen_image(str(payload["prompt"]).strip())
            elif self.path == "/api/run3d":
                result = self._run_3d(str(payload["run_id"]))
            else:
                self.send_error(404)
                return
        except Exception as exc:  # noqa: BLE001
            err = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)
            return
        body = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _gen_image(self, prompt: str) -> dict:
        from datetime import UTC, datetime
        from asset_factory.images import OpenAIImageGenerator

        if not prompt:
            raise ValueError("prompt is empty")
        run_id = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S_%fZ")
        run_dir = self.runs_root / "workshop" / run_id
        OpenAIImageGenerator().generate(
            prompt,
            run_dir / "image" / "concept.png",
            run_dir / "image" / "prompt.txt",
        )
        return {"run_id": run_id, "image_url": f"/workshop/{run_id}/image/concept.png"}

    def _run_3d(self, run_id: str) -> dict:
        from asset_factory.runners.base import RunnerRequest
        from asset_factory.runners.trellis import TrellisCommandRunner

        run_dir = self.runs_root / "workshop" / run_id
        image_path = run_dir / "image" / "concept.png"
        if not image_path.exists():
            raise FileNotFoundError(f"no concept image for run {run_id}")
        TrellisCommandRunner.from_env().run(RunnerRequest(
            concept_image=image_path,
            output_dir=run_dir / "trellis",
        ))
        return {"glb_url": f"/workshop/{run_id}/trellis/raw.glb"}


def serve_workshop(runs_root: Path, port: int) -> None:
    runs_root.mkdir(parents=True, exist_ok=True)
    _WorkshopHandler.runs_root = runs_root.resolve()
    _WorkshopHandler.initial = _find_initial_run(_WorkshopHandler.runs_root)
    handler = partial(_WorkshopHandler, directory=str(runs_root))
    with ReviewHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving workshop at http://127.0.0.1:{port}/workshop.html")
        httpd.serve_forever()
