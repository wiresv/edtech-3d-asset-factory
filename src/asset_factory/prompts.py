from __future__ import annotations

from asset_factory.models import AssetSpec, StyleMode


def build_image_prompt(spec: AssetSpec) -> str:
    base = (
        f"Create a single isolated {spec.object} as an educational science object for "
        f"grade band {spec.grade_band}. Learning goal: {spec.learning_goal} "
        "Pure white #ffffff background, subject centered and occupying 70-80% of the frame, "
        "three-quarter view showing depth, soft even ambient lighting with no cast shadows "
        "and no ground plane, full object visible, "
        "no labels, no arrows, no text, no watermark, no surrounding scene. "
        "The image must be suitable as a source image for image-to-3D asset generation."
    )
    match spec.style:
        case StyleMode.CONCEPTUAL:
            style = (
                "Style: conceptual educational 3D asset reference with simplified readable parts, "
                "clean forms, clear silhouette, gentle color separation, and structure accuracy "
                "over realism."
            )
        case StyleMode.REALISTIC:
            style = (
                "Style: realistic educational 3D asset reference with recognizable natural form, "
                "plausible material detail, accurate silhouette, and object isolation over "
                "dramatic lighting."
            )
        case _:
            raise ValueError(f"Unsupported style mode: {spec.style}")
    return f"{base} {style}"
