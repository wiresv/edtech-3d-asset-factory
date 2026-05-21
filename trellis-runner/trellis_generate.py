"""TRELLIS.2 image-to-3D wrapper matching the asset-factory runner contract.

Usage:
    trellis_generate.py <image> <output_dir> [<resolution>]
    trellis_generate.py --batch

Single-shot writes <output_dir>/raw.glb on success.

Batch mode loads the pipeline once, prints "READY", then reads
"<image>\\t<output>" lines on stdin; per line it writes <output>/raw.glb and
prints "OK\\t<output>" or "ERR\\t<output>\\t<message>". Exits on stdin EOF.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from PIL import Image  # noqa: E402

import o_voxel  # noqa: E402
from trellis2.pipelines import Trellis2ImageTo3DPipeline  # noqa: E402

# Upstream pipeline_type options are 512 / 1024 / 1024_cascade / 1536_cascade;
# 1024+ OOMs o_voxel.postprocess.to_glb on 16 GB VRAM, so both presets must use
# 512 voxel inference. Fast trims the postprocess only (smaller mesh + texture,
# skip remesh) — modest but real speedup at noticeably lower fidelity.
_QUALITY = {
    "pipeline_type": "512",
    "decimation_target": 500_000,
    "texture_size": 2048,
    "remesh": True,
}
_FAST = {
    "pipeline_type": "512",
    "decimation_target": 100_000,
    "texture_size": 1024,
    "remesh": False,
}


def _preset(resolution: int) -> dict:
    return _FAST if resolution <= 512 else _QUALITY


def _load_pipeline() -> Trellis2ImageTo3DPipeline:
    pipeline = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")
    pipeline.cuda()
    return pipeline


def _run_one(
    pipeline: Trellis2ImageTo3DPipeline,
    image_path: Path,
    output_dir: Path,
    resolution: int = 1024,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    preset = _preset(resolution)
    mesh = pipeline.run(Image.open(image_path), pipeline_type=preset["pipeline_type"])[0]
    mesh.simplify(16777216)  # upstream nvdiffrast limit
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices,
        faces=mesh.faces,
        attr_volume=mesh.attrs,
        coords=mesh.coords,
        attr_layout=mesh.layout,
        voxel_size=mesh.voxel_size,
        aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=preset["decimation_target"],
        texture_size=preset["texture_size"],
        remesh=preset["remesh"],
        remesh_band=1,
        remesh_project=0,
        verbose=True,
    )
    glb.export(output_dir / "raw.glb", extension_webp=True)


def _run_batch(pipeline: Trellis2ImageTo3DPipeline) -> None:
    print("READY", flush=True)
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line:
            continue
        try:
            image_str, output_str = line.split("\t", 1)
        except ValueError:
            print(f"ERR\t{line}\tmalformed input; expected '<image>\\t<output>'", flush=True)
            continue
        try:
            _run_one(pipeline, Path(image_str), Path(output_str))
            print(f"OK\t{output_str}", flush=True)
        except Exception as exc:  # noqa: BLE001 - report any failure per-line
            print(f"ERR\t{output_str}\t{type(exc).__name__}: {exc}", flush=True)


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--batch":
        _run_batch(_load_pipeline())
        return

    if len(sys.argv) < 3:
        print("usage: trellis_generate.py <image> <output_dir> [<resolution>]", file=sys.stderr)
        print("       trellis_generate.py --batch", file=sys.stderr)
        raise SystemExit(2)

    image_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    resolution = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    print(f"trellis_generate: image={image_path} output={output_dir} resolution={resolution}")

    _run_one(_load_pipeline(), image_path, output_dir, resolution)


if __name__ == "__main__":
    main()
