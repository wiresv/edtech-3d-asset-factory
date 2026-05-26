from __future__ import annotations

import http.server
import json
import shutil
import threading
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
SEEDS_DIR = Path(__file__).resolve().parents[2] / "assets" / "seeds"
SEEDS_CACHE_DIR = SEEDS_DIR / "cache"
SPA_ROUTES = frozenset({"/", "/workshop", "/workshop.html"})


def _list_seed_prompts() -> list[dict[str, object]]:
    from asset_factory.prompts import build_image_prompt
    from asset_factory.specs import load_asset_spec, seed_spec_paths

    if not SEEDS_DIR.is_dir():
        return []
    items: list[dict[str, object]] = []
    for path in seed_spec_paths(SEEDS_DIR):
        spec = load_asset_spec(path)
        label = spec.object[:1].upper() + spec.object[1:]
        items.append(
            {
                "id": spec.id,
                "label": label,
                "subject": spec.subject.value,
                "style": spec.style.value,
                "prompt": build_image_prompt(spec),
                "cached": (SEEDS_CACHE_DIR / f"{spec.id}.png").is_file(),
                "model_cached": (SEEDS_CACHE_DIR / f"{spec.id}.glb").is_file(),
            }
        )
    return items


def _materialize_seed(runs_root: Path, seed_id: str) -> dict:
    """Copy a seed's cached concept image (and cached GLB, if any) into a fresh workshop run."""
    if not seed_id:
        raise FileNotFoundError("missing id")
    cache_png = SEEDS_CACHE_DIR / f"{seed_id}.png"
    if not cache_png.is_file():
        raise FileNotFoundError(f"no cached image for {seed_id}")
    run_id = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S_%fZ")
    run_dir = runs_root / "workshop" / run_id
    image_dir = run_dir / "image"
    image_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cache_png, image_dir / "concept.png")
    cache_prompt = SEEDS_CACHE_DIR / f"{seed_id}.txt"
    if cache_prompt.is_file():
        shutil.copy2(cache_prompt, image_dir / "prompt.txt")
    result = {"run_id": run_id, "image_url": f"/workshop/{run_id}/image/concept.png"}
    cache_glb = SEEDS_CACHE_DIR / f"{seed_id}.glb"
    if cache_glb.is_file():
        trellis_dir = run_dir / "trellis"
        trellis_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cache_glb, trellis_dir / "raw.glb")
        result["glb_url"] = f"/workshop/{run_id}/trellis/raw.glb"
    return result


class ReviewHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True


DEFAULT_INITIAL_ASSET_ID = "chloroplast_001"


def _find_initial_run(runs_root: Path) -> dict | None:
    """Pick the newest completed chloroplast run, falling back to any newest run."""
    if not runs_root.is_dir():
        return None

    def rel(p: Path) -> str:
        return "/" + p.relative_to(runs_root).as_posix()

    def collect(asset_dir: Path) -> list[tuple[float, Path, Path, Path]]:
        out: list[tuple[float, Path, Path, Path]] = []
        if not asset_dir.is_dir():
            return out
        for run_dir in asset_dir.iterdir():
            if not run_dir.is_dir():
                continue
            prompt = run_dir / "image" / "prompt.txt"
            image = run_dir / "image" / "concept.png"
            glb = run_dir / "optimize" / "asset.glb"
            if not (prompt.exists() and image.exists() and glb.exists()):
                continue
            out.append((run_dir.stat().st_mtime, prompt, image, glb))
        return out

    candidates = collect(runs_root / DEFAULT_INITIAL_ASSET_ID)
    if not candidates:
        for asset_dir in runs_root.iterdir():
            if not asset_dir.is_dir() or asset_dir.name == "workshop":
                continue
            candidates.extend(collect(asset_dir))
    if not candidates:
        return None

    candidates.sort(reverse=True)
    _, prompt, image, glb = candidates[0]
    return {
        "prompt": prompt.read_text(encoding="utf-8"),
        "image_url": rel(image),
        "glb_url": rel(glb),
    }


class _SPAHandler(http.server.SimpleHTTPRequestHandler):
    runs_root: Path

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        super().log_message(format, *args)

    def do_GET(self) -> None:  # noqa: N802
        url = urlsplit(self.path)
        path = url.path

        if path == "/api/health":
            self._write_json(200, {"ok": True})
            return

        if path == "/api/initial":
            self._write_json(200, _find_initial_run(self.runs_root))
            return

        if path == "/api/seed-prompts":
            self._write_json(200, _list_seed_prompts())
            return

        if path == "/api/seed-image":
            try:
                seed_id = (parse_qs(url.query).get("id") or [""])[0]
                self._write_json(200, _materialize_seed(self.runs_root, seed_id))
            except FileNotFoundError as exc:
                self._write_json(404, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._write_json(500, {"error": str(exc)})
            return

        if path in SPA_ROUTES:
            self._serve_spa_index()
            return

        if path.startswith("/assets/") or path == "/favicon.svg":
            self._serve_from_dist(path)
            return

        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/run3d":
                self._stream_run_3d(str(payload["run_id"]), bool(payload.get("fast")))
                return
            if self.path == "/api/image":
                result = self._gen_image(str(payload["prompt"]).strip())
            else:
                self.send_error(404)
                return
        except Exception as exc:  # noqa: BLE001
            self._write_json(500, {"error": str(exc)})
            return
        self._write_json(200, result)

    def _stream_run_3d(self, run_id: str, fast: bool) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()

        outcome: dict[str, object] = {}

        holder: dict[str, object] = {}

        def work() -> None:
            try:
                outcome["value"] = self._run_3d(
                    run_id, fast, on_start=lambda p: holder.__setitem__("proc", p)
                )
            except Exception as exc:  # noqa: BLE001
                outcome["error"] = str(exc) or exc.__class__.__name__

        worker = threading.Thread(target=work, daemon=True)
        worker.start()
        try:
            while True:
                worker.join(timeout=2)
                if not worker.is_alive():
                    break
                self.wfile.write(b'{"status":"working"}\n')
                self.wfile.flush()
            if "error" in outcome:
                final = {"error": outcome["error"]}
            else:
                value = outcome.get("value") or {}
                final = {"status": "done", **value}  # type: ignore[dict-item]
            self.wfile.write(json.dumps(final).encode("utf-8") + b"\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            # Client canceled (aborted the request): stop the GPU build.
            _terminate(holder.get("proc"))
            return

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

    def _run_3d(self, run_id: str, fast: bool, on_start=None) -> dict:
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
                resolution=512 if fast else 1024,
            ),
            on_start=on_start,
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


def _terminate(proc: object) -> None:
    """Stop a running build subprocess. SIGTERM is signal-proxied by `docker run`
    to the container so the GPU work actually stops and `--rm` cleans up."""
    if proc is None:
        return
    try:
        proc.terminate()  # type: ignore[attr-defined]
    except (ProcessLookupError, OSError):
        pass


def serve_workshop(runs_root: Path, port: int) -> None:
    runs_root.mkdir(parents=True, exist_ok=True)

    class Handler(_SPAHandler):
        pass

    Handler.runs_root = runs_root.resolve()
    handler = partial(Handler, directory=str(runs_root))
    with ReviewHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving workshop at http://127.0.0.1:{port}/")
        httpd.serve_forever()
