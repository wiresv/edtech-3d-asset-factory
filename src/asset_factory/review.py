from __future__ import annotations

import http.server
import json
from functools import partial
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
SPA_ROUTES = frozenset({"/", "/workshop", "/workshop.html", "/review", "/review.html"})


class ReviewHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True


def write_review_html(
    run_dir: Path,
    *,
    asset_id: str,
    concept_image: str,  # noqa: ARG001 — preserved for manifest provenance compatibility
    glb_path: str,  # noqa: ARG001
    thumbnail: str,  # noqa: ARG001
    qa_passed: bool,  # noqa: ARG001
    warnings: list[str],  # noqa: ARG001
) -> Path:
    """Write a tiny meta-refresh HTML that bounces to the SPA review route.

    The SPA reads the run path from `?run=<asset>/<timestamp>` and fetches
    review data via /api/review. The relative-path computation only works if
    the run dir layout is `<runs_root>/<asset>/<timestamp>/` — which is what
    the pipeline always produces.
    """
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    rel_run = f"{run_dir.parent.name}/{run_dir.name}"
    target = f"/review?run={rel_run}"
    body = (
        "<!doctype html>\n"
        '<meta charset="utf-8">\n'
        f'<meta http-equiv="refresh" content="0; url={target}">\n'
        f"<title>Review {asset_id}</title>\n"
        f'<p>Redirecting to <a href="{target}">{target}</a>…</p>\n'
    )
    path = reports_dir / "review.html"
    path.write_text(body, encoding="utf-8")
    return path


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

    def rel(p: Path) -> str:
        return "/" + p.relative_to(runs_root).as_posix()

    return {
        "prompt": prompt.read_text(encoding="utf-8"),
        "image_url": rel(image),
        "glb_url": rel(glb),
    }


def _read_review_for(run_dir: Path, url_prefix: str) -> dict | None:
    """Assemble review JSON for a run dir. URLs are rooted at `url_prefix`.

    Manifest file paths can be absolute, so we ignore them and use the
    canonical layout produced by the pipeline.
    """
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    asset = manifest.get("asset", {})
    qa = manifest.get("qa", {})
    warnings = [*qa.get("blocking_failures", []), *qa.get("warnings", [])]
    prefix = url_prefix.rstrip("/")

    def url(rel: str) -> str:
        return f"{prefix}/{rel}" if prefix else f"/{rel}"

    return {
        "asset_id": asset.get("id", run_dir.name),
        "concept_image_url": url("image/concept.png"),
        "glb_url": url("optimize/asset.glb"),
        "thumbnail_url": url("previews/thumbnail.png"),
        "qa_passed": bool(qa.get("passed", False)),
        "warnings": [str(w) for w in warnings],
    }


class _SPAHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the React SPA + JSON API, falling through to static files.

    Two modes:
      - workshop: `runs_root` is the parent of many `<asset>/<timestamp>/` dirs.
      - single_run: `runs_root` is one such dir; `/api/review` ignores ?run= and
        returns data for the served directory itself.
    """

    runs_root: Path
    single_run: bool = False
    workshop_enabled: bool = True

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        # Match SimpleHTTPRequestHandler's default to stderr but quieter.
        super().log_message(format, *args)

    def do_GET(self) -> None:  # noqa: N802
        url = urlsplit(self.path)
        path = url.path

        if path == "/api/initial":
            initial = None if self.single_run else _find_initial_run(self.runs_root)
            self._write_json(200, initial)
            return

        if path == "/api/review":
            if self.single_run:
                data = _read_review_for(self.runs_root, url_prefix="")
            else:
                params = parse_qs(url.query)
                run_param = (params.get("run") or [""])[0].strip("/")
                if not run_param:
                    self._write_json(404, {"error": "missing run param"})
                    return
                run_dir = (self.runs_root / run_param).resolve()
                if not _under(run_dir, self.runs_root.resolve()) or not run_dir.is_dir():
                    self._write_json(404, {"error": "run not found"})
                    return
                data = _read_review_for(run_dir, url_prefix=f"/{run_param}")
            if data is None:
                self._write_json(404, {"error": "no review data"})
                return
            self._write_json(200, data)
            return

        if path in SPA_ROUTES:
            self._serve_spa_index()
            return

        if path.startswith("/assets/"):
            self._serve_from_dist(path)
            return

        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self.workshop_enabled:
            self.send_error(405)
            return
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
            self._write_json(500, {"error": str(exc)})
            return
        self._write_json(200, result)

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
        TrellisCommandRunner.from_env().run(
            RunnerRequest(
                concept_image=image_path,
                output_dir=run_dir / "trellis",
            )
        )
        return {"glb_url": f"/workshop/{run_id}/trellis/raw.glb"}

    def _serve_spa_index(self) -> None:
        index = FRONTEND_DIST / "index.html"
        if not index.is_file():
            self.send_error(
                503,
                "Frontend not built. Run `cd frontend && npm install && npm run build`.",
            )
            return
        self._serve_file(index, "text/html; charset=utf-8")

    def _serve_from_dist(self, url_path: str) -> None:
        rel = url_path.lstrip("/")
        target = (FRONTEND_DIST / rel).resolve()
        if not _under(target, FRONTEND_DIST.resolve()) or not target.is_file():
            self.send_error(404)
            return
        self._serve_file(target, self.guess_type(str(target)))

    def _serve_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if path.suffix in {".js", ".css", ".woff2", ".png", ".jpg", ".svg"}:
            # Vite emits hashed names — safe to cache aggressively.
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(data)

    def _write_json(self, status: int, body: object) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def serve_workshop(runs_root: Path, port: int) -> None:
    runs_root.mkdir(parents=True, exist_ok=True)

    class Handler(_SPAHandler):
        pass

    Handler.runs_root = runs_root.resolve()
    Handler.single_run = False
    Handler.workshop_enabled = True
    handler = partial(Handler, directory=str(runs_root))
    with ReviewHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving workshop at http://127.0.0.1:{port}/")
        httpd.serve_forever()


def serve_review(run_dir: Path, port: int) -> None:
    class Handler(_SPAHandler):
        pass

    Handler.runs_root = run_dir.resolve()
    Handler.single_run = True
    Handler.workshop_enabled = False
    handler = partial(Handler, directory=str(run_dir))
    with ReviewHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving review for {run_dir} at http://127.0.0.1:{port}/review")
        httpd.serve_forever()
