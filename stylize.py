#!/usr/bin/env python3
"""
stylize.py — turn a real photo into a stylized image that Seedance will accept.

Uses fal-ai/flux-kontext (default) or fal-ai/nano-banana/edit to transform a
real photo into a 3D cartoon / anime / illustration before feeding it to
Seedance 2.0 image-to-video (which rejects real faces, especially minors).

Usage:
    export FAL_KEY=...
    python3 stylize.py input.jpg                                  # default: 3D cartoon
    python3 stylize.py input.jpg --style anime
    python3 stylize.py input.jpg --style "Pixar 3D, soft lighting, studio bg"
    python3 stylize.py input.jpg --model nano-banana --out assets/hero/hero7/

Output: writes a PNG into --out (default: same folder, suffix _stylized.png)
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import pathlib
import sys
import time
import urllib.request
import urllib.error


STYLES = {
    "3d":     "Transform this into a 3D Pixar-style cartoon character, clean studio background, soft rim lighting, vivid colors, wholesome.",
    "anime":  "Transform this into an anime character, cel-shaded, expressive eyes, Studio Ghibli aesthetic, soft pastel background.",
    "comic":  "Transform this into a western comic book illustration, bold ink lines, halftone shading, dynamic pose.",
    "disney": "Transform this into a Disney 2D animated character, clean line art, vibrant flat colors, warm highlights.",
    "claymation": "Transform this into a claymation character (Aardman-style), visible fingerprints in the clay, warm lighting.",
}

MODELS = {
    # key:              (endpoint, payload_shape, rough $ per image, notes)
    "flux-kontext":     ("https://fal.run/fal-ai/flux-pro/kontext",          "flux",   "≈$0.04", "default, balanced quality/price"),
    "flux-kontext-max": ("https://fal.run/fal-ai/flux-pro/kontext/max",      "flux",   "≈$0.08", "higher fidelity, ~2× price"),
    "nano-banana":      ("https://fal.run/fal-ai/nano-banana/edit",          "nano",   "≈$0.04", "Google, good at face preservation"),
    "seededit":         ("https://fal.run/fal-ai/bytedance/seededit-3.0/edit","flux",  "≈$0.03", "ByteDance, cheapest, quick"),
    "gpt-image":        ("https://fal.run/fal-ai/gpt-image-1/edit-image/byok","nano",  "≈$0.07", "OpenAI gpt-image-1 via BYOK"),
    "qwen-edit":        ("https://fal.run/fal-ai/qwen-image-edit",           "flux",   "≈$0.03", "open-weights, good for anime/manga"),
    "ideogram":         ("https://fal.run/fal-ai/ideogram/v3/edit",          "flux",   "≈$0.06", "best if prompt has text/logos"),
}


def data_uri(path: pathlib.Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def stylize(image: pathlib.Path, style_prompt: str, model: str,
            out: pathlib.Path) -> pathlib.Path:
    key = os.environ.get("FAL_KEY")
    if not key:
        sys.exit("FAL_KEY not set")
    url, shape, price, _notes = MODELS[model]
    # Two common fal payload shapes for image-edit endpoints:
    #   "flux": single image_url + prompt
    #   "nano": array image_urls + prompt
    if shape == "flux":
        payload = {"prompt": style_prompt, "image_url": data_uri(image),
                   "num_images": 1, "output_format": "png"}
        # flux-kontext accepts guidance_scale + safety_tolerance; others ignore extras
        if "kontext" in url:
            payload["guidance_scale"] = 3.5
            payload["safety_tolerance"] = "2"
    else:  # "nano" — array of images
        payload = {"prompt": style_prompt, "image_urls": [data_uri(image)],
                   "num_images": 1, "output_format": "png"}

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
        method="POST",
    )
    print(f"[stylize] {model} ({price}) <- {image.name} … (style: {style_prompt[:60]}…)")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:500]}")

    images = data.get("images") or data.get("output") or []
    if not images:
        sys.exit(f"no images in reply: {json.dumps(data)[:400]}")
    img_url = images[0].get("url") if isinstance(images[0], dict) else images[0]
    if not img_url:
        sys.exit(f"no image URL: {json.dumps(images[0])[:400]}")

    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(img_url, timeout=120) as r, out.open("wb") as f:
        f.write(r.read())
    dt = time.time() - t0
    print(f"[stylize] done in {dt:.1f}s → {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=pathlib.Path, help="input photo")
    ap.add_argument("--style", default="3d",
                    help=f"preset name ({', '.join(STYLES)}) or full custom prompt")
    ap.add_argument("--model", choices=list(MODELS), default="flux-kontext",
                    help="image-edit model: " + " | ".join(
                        f"{k} ({v[2]}, {v[3]})" for k, v in MODELS.items()))
    ap.add_argument("--out", type=pathlib.Path,
                    help="output PNG path (default: <input>_stylized.png)")
    args = ap.parse_args()

    if not args.image.exists():
        sys.exit(f"not found: {args.image}")

    prompt = STYLES.get(args.style, args.style)  # preset OR custom prompt
    out = args.out or args.image.with_name(args.image.stem + "_stylized.png")
    stylize(args.image, prompt, args.model, out)


if __name__ == "__main__":
    main()
