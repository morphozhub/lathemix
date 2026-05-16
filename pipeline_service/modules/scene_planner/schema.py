from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


MaterialType = Literal["matte", "metal", "glossy", "emissive", "glass"]


class OSDPart(BaseModel):
    """One observed part of the object."""

    name: str = Field(
        ...,
        description=(
            "Short stable identifier — 'seat', 'front-left leg', 'lampshade'. "
            "Used by the Coder as a node id hint and by the Critic/Patcher as "
            "`target_node_id` for iterative refinement."
        ),
    )
    narrative: str = Field(
        ...,
        min_length=80,
        description=(
            "Two to five sentences covering shape, approximate size, position "
            "relative to the whole, material PBR cues, and any modifier cue "
            "(bend/twist/taper). Written for a 3D artist to implement. "
            "Color goes in the structured `hex_color` field — don't repeat "
            "hex in the narrative."
        ),
    )
    count_hint: str = Field(
        default="one",
        description=(
            "'one', 'four symmetric', 'two mirrored pairs', 'a single row of "
            "six'. Critical for the Coder — drives the instanced_group "
            "decision, so keep it as a structured field rather than burying "
            "it in the narrative."
        ),
    )
    motif_role: str | None = Field(
        default=None,
        description=(
            "Optional role hint — 'support', 'body', 'enclosure', "
            "'decoration'. Helps the Coder group related nodes into the "
            "right sub-group (legs_group, body_group, ...)."
        ),
    )
    # lathemix additions (Tier 1.2) for color & material discipline
    hex_color: str = Field(
        default="#808080",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description=(
            "MANDATORY 6-digit hex (#RRGGBB) for this part. Must be chosen "
            "from the CV-measured palette in the EXACT COLOR REQUIREMENT "
            "block of the prompt (or tight offset shade of one). Coder "
            "injects this directly into THREE.Color() — no approximation. "
            "Default `#808080` (mid-gray) only if palette extraction failed."
        ),
    )
    material_type: MaterialType = Field(
        default="matte",
        description=(
            "PBR material class. Coder maps to MeshStandardMaterial knobs: "
            "matte=roughness:0.85/metalness:0.0, metal=roughness:0.25/"
            "metalness:0.9, glossy=roughness:0.25/clearcoat:0.7, "
            "emissive=add emissive:hex_color, glass=transmission:0.9. "
            "Default `matte` — safe for most photographic objects."
        ),
    )


class OSD(BaseModel):
    """Object Structural Description."""

    object_type: str = Field(
        ...,
        description="Short lowercase noun — 'chair', 'goblet', 'bottle', 'car', 'lamp'.",
    )
    scene_brief: str = Field(
        ...,
        min_length=300,
        description=(
            "Markdown-formatted prose describing the whole object as if "
            "briefing a 3D artist. Expected sections (as ## headings inside "
            "the string):\n"
            "  ## Overall silhouette\n"
            "  ## Proportions\n"
            "  ## Materials and color palette\n"
            "  ## Layout and symmetry\n"
            "Typical length 600–2000 tokens. Coder reads this as the primary "
            "context — it is NOT a short summary."
        ),
    )
    parts: list[OSDPart] = Field(
        ...,
        description="Flat list of observed parts with per-part narratives.",
    )
    motif_hint: str | None = Field(
        default=None,
        description=(
            "If the object matches a known motif template (chair/table/"
            "bottle/mug/lamp/car/...), name it here. None if no clean match."
        ),
    )
    notes: str | None = Field(
        default=None,
        description="Overall caveats — occlusion, ambiguity, style cues. None if irrelevant.",
    )
