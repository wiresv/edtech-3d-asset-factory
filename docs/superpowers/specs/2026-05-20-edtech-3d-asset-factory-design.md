# EdTech 3D Asset Factory Design

Date: 2026-05-20

## Summary

Build a CLI-first developer tool that helps EdTech engineers generate app-ready educational science assets through this pipeline:

```text
asset spec -> OpenAI concept image -> TRELLIS.2 3D generation -> optimization -> QA -> export packages -> local review
```

The tool is a reproducible asset factory, not a teacher-facing creator or student sandbox. Engineers define science learning assets in checked-in specs, generate artifacts through repeatable runs, inspect visual quality in a lightweight browser review screen, and export bundles for web learning apps plus Unity and Unreal projects.

## Goals

- Generate educational science 3D assets from source specs using OpenAI image generation and TRELLIS.2.
- Support both `conceptual` and `realistic` style modes as first-class options.
- Produce reproducible run directories with all intermediate and final artifacts.
- Export app-ready packages for web, Unity, and Unreal.
- Block technically unusable assets while keeping science correctness in a human review loop.
- Design TRELLIS execution behind a runner interface so v1 can be local-first while remote GPU runners remain cleanly addable later.

## Non-Goals

- Teacher-facing or student-facing generation flows.
- Multi-user accounts, authentication, cloud storage, or hosted queues.
- Remote GPU runner implementation in v1.
- Fine-tuning OpenAI or TRELLIS.2 models.
- Rigged animation, skeletal characters, or dynamic simulations.
- Fully automated science correctness approval.
- Arbitrary non-science asset domains.

## Target User

The primary user is an EdTech engineer building learning apps, simulations, interactive lessons, or internal asset libraries. They are comfortable with CLI workflows, checked-in configuration files, build artifacts, local browser tooling, and review reports.

## Architecture

The tool will be a CLI-first reproducible asset factory. A developer writes an `asset.yaml` spec describing a science object, grade band, style mode, learning intent, export profiles, and QA thresholds. The CLI turns that spec into a versioned run directory containing generated source images, TRELLIS.2 outputs, optimized exports, previews, manifests, and reports.

Core modules:

- `spec`: validates asset specs and normalizes defaults.
- `image`: calls OpenAI `gpt-image-2` to generate concept images from the spec.
- `runner`: abstracts 3D generation. v1 ships a local TRELLIS.2 runner; remote GPU runners can be added later behind the same interface.
- `optimize`: post-processes GLBs for runtime use, including scale, orientation, texture size, and polygon and size budgets.
- `qa`: blocks severe technical failures and creates a review report.
- `export`: emits web, Unity, and Unreal asset packages.
- `review`: serves a lightweight local browser dashboard for visual QA.

Style is first-class: each asset can request `conceptual` or `realistic`, and prompt templates, QA expectations, metadata, and preview labels adjust accordingly.

## Asset Spec

A run starts from a checked-in spec:

```yaml
id: chloroplast_001
subject: biology
object: chloroplast
grade_band: "6-8"
style: conceptual
learning_goal: "Identify the outer membrane, stroma, thylakoids, and grana."
exports: ["web", "unity", "unreal"]
qa:
  max_triangles: 150000
  max_glb_mb: 25
```

Required v1 fields:

- `id`: stable asset identifier.
- `subject`: science domain such as biology, chemistry, physics, earth science, or astronomy.
- `object`: object or concept to represent as a 3D asset.
- `grade_band`: intended grade range.
- `style`: `conceptual` or `realistic`.
- `learning_goal`: short statement of what the asset teaches.
- `exports`: one or more export profiles: `web`, `unity`, `unreal`.
- `qa`: deterministic thresholds used by the QA gate.

Optional later fields can include label suggestions, hotspot definitions, canonical camera views, scale hints, curriculum standard references, and known scientific constraints.

## Data Flow

The CLI creates a versioned run directory for each generation attempt:

```text
runs/chloroplast_001/<timestamp>/
  input/asset.yaml
  image/concept.png
  image/prompt.txt
  trellis/raw.glb
  trellis/raw_report.json
  optimize/asset.glb
  previews/thumbnail.png
  previews/turntable.webm
  exports/web/
  exports/unity/
  exports/unreal/
  reports/qa.json
  reports/review.html
  manifest.json
```

Each run is immutable by default. If the spec changes or the asset is regenerated, the CLI creates a new timestamped run rather than overwriting previous artifacts.

## Manifest Contract

`manifest.json` is the main contract for app developers. It includes:

- Asset identity: `id`, object name, subject, version, and run timestamp.
- Educational metadata: grade band, learning goal, style mode, tags, and optional standards.
- Provenance: source spec path, generated image prompt, OpenAI model, TRELLIS runner, runner version, and generation timestamps.
- Files: relative paths for GLB, textures if exported separately, thumbnails, turntable previews, QA reports, and profile-specific bundles.
- Runtime hints: scale, orientation, canonical camera positions, suggested labels, suggested hotspots, and interaction notes.
- QA summary: pass/fail status, blocking failures, warnings, and measured file/poly/texture metrics.
- Review state: `generated`, `needs_review`, `needs_changes`, `approved`, or `rejected`, plus reviewer notes.

Generated assets can exist without human approval, but app-facing bundles must expose review state clearly so downstream apps can decide whether to consume only approved assets.

## OpenAI Image Generation

v1 requires OpenAI image generation rather than accepting external source images. The asset spec is the reproducible source of truth; generated concept images are intermediate artifacts retained for auditability.

The image module should:

- Build prompts from subject, object, grade band, style, and learning goal.
- Use style-specific prompt templates.
- Request a neutral object-centric composition suitable for 3D reconstruction.
- Persist the exact prompt and generated image.
- Fail the run if image generation returns no usable image.

Conceptual prompts should favor clean shapes, readable educational structure, and simplified parts. Realistic prompts should favor natural visual appearance, material plausibility, and recognizable real-world form while preserving object isolation.

## Runner Interface

The runner interface separates the pipeline from the execution environment:

```text
input: concept image + normalized generation settings
output: raw GLB + runner report
```

v1 implements a local TRELLIS.2 runner for a Linux NVIDIA environment. The runner contract should be narrow enough that future remote implementations can submit jobs to a cloud GPU queue, poll status, and download artifacts without changing the rest of the pipeline.

Runner reports should include:

- Runner type and version.
- TRELLIS.2 resolution/settings.
- Start and end timestamps.
- Exit status and error details.
- Raw output paths.
- Basic output metrics if available.

## Optimization

The optimization stage converts raw TRELLIS output into runtime-friendly assets without changing the educational intent.

Responsibilities:

- Normalize scale and orientation.
- Preserve PBR materials where available.
- Enforce configured texture and file-size budgets.
- Compute triangle count and file size metrics.
- Produce a canonical `optimize/asset.glb`.
- Generate thumbnail and turntable preview assets.

Any destructive simplification must be reflected in reports so reviewers understand what changed.

## Export Profiles

The tool supports three v1 export profiles:

- `web`: GLB, manifest, thumbnail, turntable preview, and JSON metadata for Three.js, React Three Fiber, Babylon.js, or similar web learning apps.
- `unity`: Unity-oriented folder structure with GLB, manifest, preview media, and import notes.
- `unreal`: Unreal-oriented folder structure with GLB, manifest, preview media, and import notes.

Web is the default mental model, but Unity and Unreal exports are explicit first-class profiles. Each profile may define its own file layout, metadata adapter, and validation checks.

## QA and Review

QA is split into deterministic blocking checks and human educational review.

Blocking checks fail the export when the asset is technically unusable:

- OpenAI image generation failed or returned no usable image.
- TRELLIS.2 failed or produced no GLB.
- GLB cannot be parsed.
- Required mesh, material, or base color data is missing.
- A profile-specific required PBR channel is missing.
- File size, texture size, or triangle count exceeds configured hard limits.
- Manifest is invalid or missing required fields.
- Export profile packaging fails.

Non-blocking checks create warnings:

- Possible visual artifact, holes, floating geometry, bad silhouette, or unreadable detail.
- Science correctness needs review.
- Conceptual model may be too realistic, or realistic model may be too stylized.
- Object scale or orientation may need adjustment.
- Suggested labels or hotspots need human confirmation.

The local browser review screen should show the concept image, interactive 3D preview, turntable, QA summary, manifest metadata, and export paths. It should let an engineer mark the run `approved`, `rejected`, or `needs_changes` with notes. The review state is stored in the run manifest and copied into export bundles.

## CLI Surface

The initial CLI should stay small:

```text
asset-factory generate path/to/asset.yaml
asset-factory review runs/<asset-id>/<timestamp>
asset-factory export runs/<asset-id>/<timestamp> --profile web
asset-factory qa runs/<asset-id>/<timestamp>
```

`generate` performs the complete path from spec through export unless a blocking failure occurs. `review` opens the local dashboard. `qa` reruns deterministic checks. `export` rebuilds profile packages from an existing optimized asset.

## MVP Scope

v1 should support a narrow but complete path:

- CLI command to generate one asset from one `asset.yaml`.
- OpenAI-required concept image generation using `gpt-image-2`.
- Local TRELLIS.2 runner behind a runner interface.
- Two science style modes: `conceptual` and `realistic`.
- Export profiles for web, Unity, and Unreal.
- Deterministic blocking QA for severe technical issues.
- Local browser review dashboard.
- Versioned run directories with reproducible artifacts.
- Manifest-driven asset packages for app integration.

## Testing Strategy

Testing should focus on reproducibility, package validity, and catching broken 3D outputs early.

Core test areas:

- Spec validation: required fields, defaults, invalid style and export values, QA thresholds.
- Prompt generation: conceptual versus realistic prompt templates produce expected instructions.
- Runner abstraction: local TRELLIS runner can be mocked, and remote runners can later satisfy the same contract.
- Manifest generation: stable schema and valid paths.
- Export profiles: web, Unity, and Unreal packages include required files and metadata.
- QA checks: intentionally broken GLB, missing texture, and oversized asset cases fail correctly.
- Review state: review decisions and notes persist and propagate into exports.

The pipeline should include a mock runner before requiring TRELLIS.2 so the artifact layout, QA behavior, exports, and review UI can be developed on ordinary machines.

## V1 Technical Decisions

- Implementation language: Python for the CLI, orchestration, OpenAI calls, spec validation, runner interface, and TRELLIS integration. The review dashboard can be a small Python-served static web app using Three.js for GLB preview.
- CLI framework: Typer.
- Spec and manifest validation: Pydantic models with JSON Schema export for downstream tooling.
- GLB inspection: Python-based parsing for deterministic QA, with profile hooks that can later call stronger external optimizers.
- GLB optimization: start with conservative validation, scale/orientation normalization, preview generation, and size checks. Add mesh simplification only when the original artifact violates configured budgets.
- Material requirements: base mesh, material assignment, and base color are required by default. Roughness, metallic, and opacity are recorded when present and warning-level when absent unless an export profile marks them required.
- Review state: stored in the run manifest for v1. A top-level registry is deferred until there are multiple asset collections or team workflows.
- Seed asset set: start with biology, physics, and earth science because they provide both conceptual and realistic use cases.

Initial seed assets:

1. Chloroplast, conceptual.
2. Plant cell, conceptual.
3. Mitochondrion, conceptual.
4. Lever, conceptual.
5. Pulley, conceptual.
6. Trilobite fossil, realistic.
7. Basalt rock sample, realistic.
8. Quartz crystal, realistic.
9. Human tooth cross-section, realistic with simplified educational structure.
10. Fern leaf underside with spores, realistic.

## Milestones

1. Spec schema, CLI shell, and run directory layout.
2. OpenAI image generation integration.
3. Mock runner and full artifact pipeline without TRELLIS.2.
4. Local TRELLIS.2 runner integration.
5. GLB optimization and deterministic QA.
6. Web, Unity, and Unreal export profiles.
7. Browser review dashboard.
8. Seed science asset set: 5 conceptual and 5 realistic assets.

## Deferred Decisions

- Remote GPU runner protocol and provider.
- Team workflow model for shared asset review.
- Curriculum standards taxonomy.
- Deeper mesh simplification and texture compression strategy.
- Whether external source images should be accepted after the OpenAI-required v1 path is stable.
