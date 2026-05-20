from pathlib import Path

from asset_factory.review import _find_initial_run, serve_workshop


def _make_run(run_dir: Path, *, with_glb: bool = True) -> Path:
    (run_dir / "image").mkdir(parents=True)
    (run_dir / "image" / "prompt.txt").write_text("a chloroplast", encoding="utf-8")
    (run_dir / "image" / "concept.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    if with_glb:
        (run_dir / "optimize").mkdir()
        (run_dir / "optimize" / "asset.glb").write_bytes(b"glb")
    return run_dir


def test_find_initial_run_returns_newest_completed(tmp_path: Path):
    runs = tmp_path
    a = _make_run(runs / "cell_001" / "20260101T000000Z")
    b = _make_run(runs / "cell_002" / "20260201T000000Z")
    import os, time
    os.utime(a, (time.time() - 60, time.time() - 60))
    os.utime(b, None)

    initial = _find_initial_run(runs)

    assert initial is not None
    assert initial["prompt"] == "a chloroplast"
    assert initial["image_url"].endswith("cell_002/20260201T000000Z/image/concept.png")
    assert initial["glb_url"].endswith("cell_002/20260201T000000Z/optimize/asset.glb")


def test_find_initial_run_skips_incomplete_and_workshop(tmp_path: Path):
    _make_run(tmp_path / "workshop" / "20260101T000000Z")
    _make_run(tmp_path / "cell_001" / "20260101T000000Z", with_glb=False)

    assert _find_initial_run(tmp_path) is None


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
