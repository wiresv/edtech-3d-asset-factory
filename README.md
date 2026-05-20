# EdTech 3D Asset Factory

CLI-first developer tool for generating educational science 3D assets from checked-in specs.

Pipeline: `asset.yaml` → OpenAI concept image → TRELLIS.2 image-to-3D → optimize → QA → web/Unity/Unreal export bundles, with an interactive browser workshop for prompt-driven generation and 3D preview.

## Reference Demo

[![TRELLIS.2 image-to-3D demo](docs/assets/trellis-demo.gif)](https://x.com/HowToAI_/status/2056387308287676819)

Click the GIF to open the original X post.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

## CLI

```text
asset-factory generate       Generate a complete asset run from an asset.yaml spec.
asset-factory batch          Generate multiple specs over one warm TRELLIS subprocess
                             (no per-asset model reload).
asset-factory qa             Run deterministic QA checks against an existing run.
asset-factory export         Rebuild an export profile from an existing run.
asset-factory workshop       Interactive prompt → image → 3D server.
asset-factory precache-seeds Pre-generate concept images for every seed spec.
```

## Seed Specs

`assets/seeds/` contains 10 initial science specs: 5 conceptual (biology, physics) and 5 realistic
(biology, earth science).

Run one against the mock runner — works without OpenAI credentials or a GPU:

```bash
asset-factory generate assets/seeds/chloroplast_conceptual.yaml --runner mock
```

The generated run directory:

```text
runs/chloroplast_001/<timestamp>/
  image/concept.png
  image/prompt.txt
  trellis/raw.glb
  trellis/raw_report.json
  optimize/asset.glb
  previews/thumbnail.png
  previews/turntable.webm
  exports/{web,unity,unreal}/asset.glb
  reports/qa.json
  manifest.json
```

Inspect the manifest:

```bash
python -m json.tool runs/chloroplast_001/<timestamp>/manifest.json
```

## TRELLIS.2 Runner Contract

The TRELLIS runner is invoked through `TRELLIS2_COMMAND` (single-shot) or `TRELLIS2_BATCH_COMMAND`
(warm process). Placeholders the asset factory substitutes:

- `{image}` — concept image path
- `{output}` — TRELLIS output directory
- `{resolution}` — voxel resolution

The command must create `{output}/raw.glb`. The asset factory writes `{output}/raw_report.json`
with stdout, stderr, return code, timing, and any failure details.

Batch mode protocol (`TRELLIS2_BATCH_COMMAND`): the process prints `READY` once loaded, then reads
`<image>\t<output>` lines on stdin; per line it writes `<output>/raw.glb` and prints
`OK\t<output>` or `ERR\t<output>\t<message>`. Exits on stdin EOF. This keeps the model resident
in VRAM across many assets.

## Local TRELLIS.2 Inference (Docker, Blackwell)

The companion repo `trellis2-runner` ships a Blackwell-compatible Docker image and a wrapper
script that satisfies both protocols.

Requirements: Linux host with an NVIDIA GPU (tested on RTX 5080 / sm_120), Docker with the NVIDIA
Container Toolkit, `OPENAI_API_KEY` for concept image generation, and TRELLIS.2 weights cached
under `~/.cache/huggingface`.

Build the image:

```bash
git clone https://github.com/wiresv/trellis2-runner.git
cd trellis2-runner
docker build -t trellis2:blackwell .
```

Single-shot generation:

```bash
export OPENAI_API_KEY="sk-…"
export TRELLIS2_COMMAND='docker run --rm --gpus all \
  -e HF_HUB_OFFLINE=1 \
  -v /root/.cache/huggingface:/root/.cache/huggingface \
  -v {image}:/work/concept.png:ro \
  -v {output}:/work/output \
  trellis2:blackwell /work/concept.png /work/output {resolution}'

asset-factory generate assets/seeds/chloroplast_conceptual.yaml --runner trellis
```

Batch (one container, many assets, no per-asset model reload):

```bash
export TRELLIS2_BATCH_COMMAND='docker run --rm -i --gpus all \
  -e HF_HUB_OFFLINE=1 \
  -v /root/.cache/huggingface:/root/.cache/huggingface \
  -v '"$PWD"'/runs:/work/runs \
  trellis2:blackwell --batch'

asset-factory batch \
  assets/seeds/chloroplast_conceptual.yaml \
  assets/seeds/mitochondrion_conceptual.yaml \
  --runner trellis
```

The batch mount must expose every `{output}` path the wrapper will be asked to write — keep all
runs under one parent dir (e.g. `runs/`) and bind that dir in.

## Workshop UI

`asset-factory workshop` serves an interactive prompt → image → 3D browser app on `127.0.0.1:8765`.
It reuses the same TRELLIS runner contract, so `OPENAI_API_KEY` and `TRELLIS2_COMMAND` must be set
in the launching shell.

```bash
cd frontend && npm install && npm run build && cd ..
asset-factory workshop --port 8765
```

The workshop persists each generation under `runs/workshop/<timestamp>/` so concept images and
GLBs survive restarts. Cached seed concept images live under `assets/seeds/cache/` and can be
pre-generated with `asset-factory precache-seeds` so the "Try one" chips in the UI load
instantly instead of waiting on OpenAI.
