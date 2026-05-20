import json
from pathlib import Path

from asset_factory.review import (
    _find_initial_run,
    _read_review_for,
    serve_review,
    serve_workshop,
    write_review_html,
)


def _make_run(run_dir: Path, *, with_glb: bool = True) -> Path:
    (run_dir / "image").mkdir(parents=True)
    (run_dir / "image" / "prompt.txt").write_text("a chloroplast", encoding="utf-8")
    (run_dir / "image" / "concept.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    if with_glb:
        (run_dir / "optimize").mkdir()
        (run_dir / "optimize" / "asset.glb").write_bytes(b"glb")
    return run_dir


def _write_manifest(run_dir: Path, *, asset_id: str, passed: bool, warnings: list[str]) -> None:
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "asset": {"id": asset_id},
                "qa": {"passed": passed, "warnings": warnings, "blocking_failures": []},
            }
        ),
        encoding="utf-8",
    )


def test_write_review_html_redirects_to_spa(tmp_path: Path):
    run_dir = tmp_path / "chloroplast_001" / "20260520T100000Z"
    run_dir.mkdir(parents=True)

    path = write_review_html(
        run_dir,
        asset_id="chloroplast_001",
        concept_image="image/concept.png",
        glb_path="optimize/asset.glb",
        thumbnail="previews/thumbnail.png",
        qa_passed=True,
        warnings=[],
    )

    assert path == run_dir / "reports" / "review.html"
    body = path.read_text(encoding="utf-8")
    assert "chloroplast_001/20260520T100000Z" in body
    assert "/review?run=chloroplast_001/20260520T100000Z" in body
    assert "http-equiv=\"refresh\"" in body


def test_find_initial_run_returns_newest_completed(tmp_path: Path):
    runs = tmp_path
    a = _make_run(runs / "cell_001" / "20260101T000000Z")
    b = _make_run(runs / "cell_002" / "20260201T000000Z")
    # mtime: b newer than a
    import os, time
    os.utime(a, (time.time() - 60, time.time() - 60))
    os.utime(b, None)

    initial = _find_initial_run(runs)

    assert initial is not None
    assert initial["prompt"] == "a chloroplast"
    assert initial["image_url"].endswith("cell_002/20260201T000000Z/image/concept.png")
    assert initial["glb_url"].endswith("cell_002/20260201T000000Z/optimize/asset.glb")


def test_find_initial_run_skips_incomplete_and_workshop(tmp_path: Path):
    _make_run(tmp_path / "workshop" / "20260101T000000Z")  # excluded
    _make_run(tmp_path / "cell_001" / "20260101T000000Z", with_glb=False)  # incomplete

    assert _find_initial_run(tmp_path) is None


def test_read_review_for_returns_canonical_urls(tmp_path: Path):
    run_dir = tmp_path / "chloroplast_001" / "20260520T100000Z"
    run_dir.mkdir(parents=True)
    _write_manifest(
        run_dir,
        asset_id="chloroplast_001",
        passed=False,
        warnings=["Bad silhouette"],
    )

    data = _read_review_for(run_dir, url_prefix="/chloroplast_001/20260520T100000Z")

    assert data == {
        "asset_id": "chloroplast_001",
        "concept_image_url": "/chloroplast_001/20260520T100000Z/image/concept.png",
        "glb_url": "/chloroplast_001/20260520T100000Z/optimize/asset.glb",
        "thumbnail_url": "/chloroplast_001/20260520T100000Z/previews/thumbnail.png",
        "qa_passed": False,
        "warnings": ["Bad silhouette"],
    }


def test_read_review_for_single_run_prefix(tmp_path: Path):
    _write_manifest(tmp_path, asset_id="demo", passed=True, warnings=[])

    data = _read_review_for(tmp_path, url_prefix="")

    assert data is not None
    assert data["asset_id"] == "demo"
    assert data["glb_url"] == "/optimize/asset.glb"
    assert data["qa_passed"] is True


def test_read_review_for_missing_manifest_returns_none(tmp_path: Path):
    assert _read_review_for(tmp_path, url_prefix="") is None


def test_serve_review_binds_to_localhost(monkeypatch, tmp_path: Path):
    captured: dict = {}

    class FakeServer:
        allow_reuse_address = False

        def __init__(self, address, handler):
            captured["address"] = address
            captured["handler"] = handler

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def serve_forever(self):
            captured["served"] = True

    monkeypatch.setattr("asset_factory.review.ReviewHTTPServer", FakeServer)

    serve_review(tmp_path, 4321)

    assert captured["address"] == ("127.0.0.1", 4321)
    assert captured["served"] is True


def test_serve_workshop_binds_to_localhost(monkeypatch, tmp_path: Path):
    captured: dict = {}

    class FakeServer:
        allow_reuse_address = False

        def __init__(self, address, handler):
            captured["address"] = address

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def serve_forever(self):
            captured["served"] = True

    monkeypatch.setattr("asset_factory.review.ReviewHTTPServer", FakeServer)

    serve_workshop(tmp_path / "runs", 7777)

    assert captured["address"] == ("127.0.0.1", 7777)
    assert captured["served"] is True
    assert (tmp_path / "runs").is_dir()
