#!/usr/bin/env python3
"""Render original, transparent cloud banks with NumPy and Pillow.

Run python tools/generate_clouds.py from the repository root. The frontend
serves the generated WebPs directly and has no rendering dependency.
"""

from pathlib import Path

import numpy as np
from PIL import Image

SIZE = (960, 420)
OUTPUT_SIZE = (1600, 700)
OUTPUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "clouds"
BANKS = {
    "ridge": (311, [(0.30, 0.67, 0.25, 0.22), (0.56, 0.57, 0.25, 0.29), (0.73, 0.68, 0.18, 0.24)]),
    "tower": (817, [(0.29, 0.70, 0.23, 0.20), (0.48, 0.54, 0.22, 0.32), (0.66, 0.63, 0.24, 0.25)]),
    "shelf": (537, [(0.24, 0.76, 0.20, 0.17), (0.47, 0.69, 0.27, 0.22), (0.72, 0.72, 0.23, 0.20)]),
    "bank": (125, [(0.27, 0.71, 0.23, 0.20), (0.52, 0.63, 0.25, 0.27), (0.73, 0.65, 0.22, 0.25)]),
}


def fbm(rng, first_scale, octaves, persistence):
    """Build fractal value noise from successively finer interpolated grids."""
    field = np.zeros(SIZE[::-1], dtype=np.float32)
    amplitude = 1.0
    for level in range(octaves):
        columns = first_scale * 2 ** level
        rows = max(3, round(columns * SIZE[1] / SIZE[0]))
        grid = rng.normal(0, 1, (rows, columns)).astype(np.float32)
        field += amplitude * np.asarray(Image.fromarray(grid).resize(SIZE, Image.Resampling.BICUBIC))
        amplitude *= persistence
    return field


def smoothstep(start, stop, values):
    fraction = np.clip((values - start) / (stop - start), 0, 1)
    return fraction ** 2 * (3 - 2 * fraction)


def render(seed, lobes):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:SIZE[1], 0:SIZE[0]].astype(np.float32)
    x /= SIZE[0]
    y /= SIZE[1]
    shape_noise = fbm(rng, 12, 6, 0.51)
    detail = fbm(rng, 25, 5, 0.51)
    warp_x = x + 0.012 * fbm(rng, 13, 5, 0.50)
    warp_y = y + 0.026 * fbm(rng, 12, 5, 0.53)
    surface = np.zeros_like(x)
    density = np.full_like(x, -3.0)

    billows = list(lobes)
    for cx, cy, rx, ry in lobes:
        for _ in range(11):
            angle = rng.uniform(np.pi, 2 * np.pi)
            size = rng.uniform(0.18, 0.48)
            billows.append((cx + rx * 0.77 * np.cos(angle), cy + ry * 0.76 * np.sin(angle), rx * size, ry * size))

    for cx, cy, rx, ry in billows:
        radial = 1 - ((warp_x - cx) / rx) ** 2 - ((warp_y - cy) / ry) ** 2
        radial += 0.19 * shape_noise + 0.095 * detail
        density = np.maximum(density, radial)
        depth = np.sqrt(np.clip(radial, 0, 1.5)) * (0.24 + 1.4 * rx)
        surface = np.maximum(surface, depth)

    fade = smoothstep(0.035, 0.16, x) * smoothstep(0.035, 0.16, 1 - x)
    fade *= smoothstep(0.008, 0.11, 1 - y)
    alpha = smoothstep(-0.11, 0.32, density) * fade

    soft_depth = np.asarray(Image.fromarray(surface).resize((320, 140), Image.Resampling.BILINEAR)
                            .resize(SIZE, Image.Resampling.BICUBIC))
    dy, dx = np.gradient(soft_depth)
    light = np.clip((dy * 54 + dx * 34 + 0.8) / np.sqrt(1 + (dy * 53) ** 2 + (dx * 53) ** 2), -1, 1)
    upper_light = 1 - smoothstep(0.23, 0.83, y)
    shade = np.clip(0.31 + 0.28 * upper_light + 0.19 * light
                    + 0.087 * shape_noise + 0.036 * detail, 0.05, 1)
    cool_shadow = np.array([153, 162, 174])
    soft_highlight = np.array([243, 246, 247])
    rgb = cool_shadow + shade[..., None] * (soft_highlight - cool_shadow)
    rgba = np.dstack((rgb, alpha * 255)).clip(0, 255).astype(np.uint8)
    return Image.fromarray(rgba).resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, (seed, lobes) in BANKS.items():
        path = OUTPUT / f"{name}.webp"
        render(seed, lobes).save(path, "WEBP", quality=76, method=6)
        print(f"{path.name}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
