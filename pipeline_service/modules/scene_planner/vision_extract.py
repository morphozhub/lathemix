"""CV color extraction for reference images.

Extracts dominant colors from prompt image foreground pixels so the LLM coder
gets concrete hex values instead of hallucinating "wood brown" or "navy blue".

Lightweight: pure PIL + numpy + Counter, no scikit-learn / no kmeans.
Algorithm: background removal (edge-pixel median) -> RGB quantization to 8
levels/channel -> top-N count -> merge near-duplicates (L1 < 80) -> normalize.

Origin: adapted from kostik46/signal-mesh (R4 innovator). Stripped of contour
and lathe-profile code — only color path retained for lathe-v5.
"""
from __future__ import annotations

import io
from collections import Counter
from typing import List, Tuple

import numpy as np
from PIL import Image


def _remove_background(arr: np.ndarray, edge_diff_threshold: int = 30) -> np.ndarray:
    """Return boolean mask of foreground pixels.

    Background is estimated as the median of edge-row/column pixels. Any pixel
    farther than `edge_diff_threshold` (euclidean distance) is foreground.
    Works well on photographs with relatively uniform borders (sn12domain.org
    prompts have white/grey/black uniform backgrounds).
    """
    h, w = arr.shape[:2]
    edge_pixels = np.concatenate([
        arr[0, :, :3], arr[-1, :, :3],
        arr[:, 0, :3], arr[:, -1, :3],
    ])
    bg_color = np.median(edge_pixels, axis=0).astype(np.float32)
    diff = np.sqrt(np.sum((arr[..., :3].astype(np.float32) - bg_color) ** 2, axis=2))
    return diff > edge_diff_threshold


def extract_dominant_colors(
    image_bytes: bytes,
    n: int = 5,
    *,
    min_fraction: float = 0.02,
    merge_l1: int = 80,
) -> List[Tuple[int, float]]:
    """Extract up to `n` dominant colors from the foreground of an image.

    Returns list of (hex_int, weight) sorted by weight descending.
    `hex_int` is a 24-bit int matching Three.js `0xRRGGBB` notation.
    `weight` is fraction of foreground pixels (0..1).

    Robust to corrupt/odd images: returns a single gray fallback on any
    failure so callers can safely use the result without exception handling.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # Downsample big images for speed (color statistics don't need full res)
        if max(img.size) > 512:
            img.thumbnail((512, 512), Image.LANCZOS)
        arr = np.array(img)

        fg_mask = _remove_background(arr)
        fg_pixels = arr[fg_mask]
        if len(fg_pixels) < 100:
            # Background detection failed (e.g. busy background) — use all pixels
            fg_pixels = arr.reshape(-1, 3)

        # Per-bin saturation-aware representative: bin pixels by quantized RGB,
        # but emit the MOST SATURATED pixel in each bin (preserves vibrancy of
        # vivid colors that would otherwise be averaged into muted tones).
        bins = (fg_pixels // 32).astype(int)
        bin_ids = bins[:, 0] * 4096 + bins[:, 1] * 64 + bins[:, 2]
        unique_bins, bin_counts = np.unique(bin_ids, return_counts=True)
        top_idx = np.argsort(-bin_counts)[: n * 4]
        total = len(fg_pixels)

        # Pre-compute saturation per pixel (HSV V = max, sat = (max-min)/max)
        fg_norm = fg_pixels.astype(np.float32) / 255.0
        max_ch = fg_norm.max(axis=1)
        min_ch = fg_norm.min(axis=1)
        sats = np.where(max_ch > 0, (max_ch - min_ch) / np.maximum(max_ch, 1e-6), 0)

        candidates: List[Tuple[Tuple[int, int, int], float]] = []
        for bin_id, count in zip(unique_bins[top_idx], bin_counts[top_idx]):
            frac = count / total
            if frac < min_fraction:
                continue
            bin_mask = bin_ids == bin_id
            rep = fg_pixels[bin_mask][sats[bin_mask].argmax()]
            candidates.append((tuple(int(c) for c in rep), frac))

        # Merge similar (L1 < merge_l1) keeping first-seen representative
        merged: List[Tuple[Tuple[int, int, int], float]] = []
        for color, frac in candidates:
            dup_idx = None
            for i, (m_rgb, m_frac) in enumerate(merged):
                if sum(abs(int(a) - int(b)) for a, b in zip(color, m_rgb)) < merge_l1:
                    dup_idx = i
                    break
            if dup_idx is not None:
                m_rgb, m_frac = merged[dup_idx]
                merged[dup_idx] = (m_rgb, m_frac + frac)
            elif len(merged) < n:
                merged.append((color, frac))

        # Normalize so weights sum to 1.0 (fg-fraction)
        total_w = sum(f for _, f in merged) or 1.0
        result: List[Tuple[int, float]] = []
        for (r, g, b), frac in sorted(merged, key=lambda x: -x[1]):
            hex_int = (int(r) << 16) | (int(g) << 8) | int(b)
            result.append((hex_int, frac / total_w))
        return result or [(0x808080, 1.0)]
    except Exception:
        # Any failure → safe gray fallback. Caller should still get usable hint.
        return [(0x808080, 1.0)]


def format_palette_text(palette: List[Tuple[int, float]]) -> str:
    """Render palette as a compact text block for LLM prompt injection."""
    lines = []
    for hex_int, weight in palette:
        pct = round(weight * 100)
        lines.append(f"  - 0x{hex_int:06X} (~{pct}%)")
    return "\n".join(lines)


# Convenience for callers that only need the prompt block.
def palette_directive(image_bytes: bytes, n: int = 5) -> str:
    """Build the full 'EXACT COLOR REQUIREMENT' block from raw image bytes.

    Returns empty string if image_bytes is None/empty — caller should skip
    injection in that case.
    """
    if not image_bytes:
        return ""
    palette = extract_dominant_colors(image_bytes, n=n)
    if not palette:
        return ""
    body = format_palette_text(palette)
    return (
        "\n\n=== EXACT COLOR REQUIREMENT ===\n"
        "Dominant colors detected in the reference image (CV palette):\n"
        f"{body}\n\n"
        "You MUST use these EXACT hex values for material colors:\n"
        "- Background / largest surface → the highest-weight color\n"
        "- Accents and details → lower-weight colors\n"
        "- For shading variation, use lighter/darker offsets of THESE hex, "
        "do NOT introduce unrelated palette entries.\n"
        "- Three.js literal: `new THREE.Color(0xAABBCC)` — no 'brown' "
        "string names, no Math.random color picks.\n"
        "- Approximating, blending, or 'improving' the palette is a "
        "disqualification-level error."
    )
