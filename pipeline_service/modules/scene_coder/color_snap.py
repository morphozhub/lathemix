"""Deterministic color-snap post-processor.

After the LLM coder emits JS, this module walks every `0xRRGGBB` literal in
the code and snaps it to the nearest CV-extracted palette color (within a
tolerance). It's the safety net for cases where the LLM ignored the palette
directive — even if it hallucinated colors, we force the output back onto
the measured palette.

Notes:
- Whitelist: only `0xRRGGBB` hex literals in `color: 0x…` / `new THREE.Color(0x…)`
  patterns are touched. Anything else (e.g. user-named consts, fragment
  shaders, build numbers) is left alone.
- Tolerance: by default a literal is snapped if its nearest palette color is
  within `tolerance=80` L1 RGB distance. Beyond that we leave the literal
  intact (the LLM may have intended an unrelated color).
- Idempotent: re-running on already-snapped JS is a no-op.
"""
from __future__ import annotations

import re
from typing import List, Tuple

# We only snap inside the THREE color-assignment patterns where a hex shows
# up. Matches:
#   color: 0xABCDEF
#   new THREE.Color(0xABCDEF)
#   setHex(0xABCDEF)
#   emissive: 0xABCDEF
_HEX_RE = re.compile(
    r"(color\s*:\s*|new\s+THREE\.Color\s*\(\s*|setHex\s*\(\s*|emissive\s*:\s*)"
    r"0x([0-9A-Fa-f]{6})"
)


def _l1(rgb_a: Tuple[int, int, int], rgb_b: Tuple[int, int, int]) -> int:
    return abs(rgb_a[0] - rgb_b[0]) + abs(rgb_a[1] - rgb_b[1]) + abs(rgb_a[2] - rgb_b[2])


def _to_rgb(hex_int: int) -> Tuple[int, int, int]:
    return ((hex_int >> 16) & 0xFF, (hex_int >> 8) & 0xFF, hex_int & 0xFF)


def snap_colors_to_palette(
    js_code: str,
    palette: List[Tuple[int, float]],
    *,
    tolerance: int = 80,
) -> Tuple[str, int]:
    """Snap hex literals in js_code to nearest palette color.

    Returns (modified_js, num_swaps). Only literals whose nearest palette
    distance is <= tolerance are swapped.
    """
    if not palette:
        return js_code, 0

    palette_rgb = [(_to_rgb(h), w) for h, w in palette]
    counter = {"swaps": 0}

    def _replace(match: re.Match) -> str:
        prefix = match.group(1)
        hex_str = match.group(2)
        hex_int = int(hex_str, 16)
        rgb = _to_rgb(hex_int)
        best_dist = None
        best_hex = None
        for p_rgb, _w in palette_rgb:
            d = _l1(rgb, p_rgb)
            if best_dist is None or d < best_dist:
                best_dist = d
                best_hex = (p_rgb[0] << 16) | (p_rgb[1] << 8) | p_rgb[2]
        if best_hex is None or best_dist > tolerance:
            return match.group(0)  # leave intact
        if best_hex == hex_int:
            return match.group(0)  # already on palette
        counter["swaps"] += 1
        return f"{prefix}0x{best_hex:06X}"

    new_code = _HEX_RE.sub(_replace, js_code)
    return new_code, counter["swaps"]
