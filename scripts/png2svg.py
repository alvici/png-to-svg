"""png2svg: PNG -> SVG, with colour variants, icons, audit and visual check.

Usage (on Windows use `python` or `py -3` instead of `python3`):
  python png2svg.py input.png --list-options                 # which variants this image offers
  python png2svg.py input.png out_dir                        # default variant
  python png2svg.py input.png out_dir --variants original,white,black --icons --compare
  python png2svg.py folder_png/ out_dir --variants all       # whole folder

Output per image (in out_dir):  <name>-<variant>.svg, optional <name>-<variant>_compare.png,
icons/ (favicon + app icons), and a JSON report printed to stdout.
"""
import os, re, io, json, argparse, tempfile
import numpy as np
from PIL import Image
import vtracer

from variants import (background, source_type, normalize_variants, make_variant,
                      silhouette_svg, export_icons, COLOR_OPTIONS, MONO_OPTIONS)
from render import render_to_array, available
from svg_audit import audit

KEY = (255, 0, 255)   # stand-in colour for transparent pixels while tracing


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3: h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def detect_gradient(rgba, bg):
    """Return (top_rgb, bottom_rgb, y0, y1) if the foreground is one vertical gradient, else None."""
    rgb = rgba[..., :3].astype(int)
    if bg is None:
        solid = rgba[..., 3] > 250
    else:
        solid = (np.abs(rgb - np.array(bg)).sum(-1) > 250) & (rgba[..., 3] > 250)
    if solid.sum() < 100:
        return None
    ys = np.nonzero(solid)[0]
    cols = rgb[solid].astype(float)
    if not 5 < cols.std(0).sum() < 60:
        return None
    t = (ys - ys.min()) / max(1, ys.max() - ys.min())
    top = cols[t < 0.05].mean(0); bottom = cols[t > 0.95].mean(0)
    pred = top + np.outer(t, bottom - top)
    if np.abs(pred - cols).mean() >= 8:
        return None
    return top.round().astype(int).tolist(), bottom.round().astype(int).tolist(), int(ys.min()), int(ys.max())


def classify(rgba):
    bg, fg = background(rgba)
    rgb = rgba[..., :3].astype(int)[fg]
    q = rgb // 16
    buckets = len(np.unique(q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2])) if len(q) else 0
    grad = detect_gradient(rgba, bg)
    if grad:
        kind = "gradient-shape"
    elif buckets <= 4:
        kind = "flat"
    elif buckets <= 64:
        kind = "multicolor"
    else:
        kind = "photo"
    return dict(bg=bg, fg=fg, buckets=buckets, grad=grad, kind=kind)


def _path_box(d, tx, ty):
    nums = [float(n) for n in re.findall(r"-?\d*\.?\d+", d)]
    xs = nums[0::2]; ys = nums[1::2]
    return min(xs) + tx, min(ys) + ty, max(xs) + tx, max(ys) + ty


def trace_original(rgba, info, colors, speckle):
    """Colour trace with the background removed. Returns svg body (paths) and viewBox size."""
    h, w = rgba.shape[:2]
    transparent = info["bg"] is None
    rgb = rgba[..., :3].copy()
    if transparent:
        rgb[rgba[..., 3] < 128] = KEY
    img = Image.fromarray(rgb.astype(np.uint8))
    q = img.quantize(colors=colors + (1 if transparent else 0), dither=Image.Dither.NONE).convert("RGB")
    buf = io.BytesIO(); q.save(buf, "PNG")
    svg = vtracer.convert_raw_image_to_svg(
        buf.getvalue(), img_format="png", colormode="color",
        hierarchical="cutout" if transparent else "stacked", mode="spline",
        filter_speckle=speckle, color_precision=6, layer_difference=16,
        corner_threshold=60, length_threshold=4.0, splice_threshold=45, path_precision=2)
    keep = []
    for d, fill, tx, ty in re.findall(
            r'<path d="([^"]+)" fill="(#[0-9A-Fa-f]{6})" transform="translate\(([-\d.]+),([-\d.]+)\)"', svg):
        c = np.array(_hex_to_rgb(fill))
        tx, ty = float(tx), float(ty)
        if transparent and np.abs(c - KEY).sum() < 90:
            continue                                   # transparent area
        if not transparent and np.abs(c - np.array(info["bg"])).sum() < 40:
            x0, y0, x1, y1 = _path_box(d, tx, ty)
            if x0 <= 1 or y0 <= 1 or x1 >= w - 1 or y1 >= h - 1:
                continue                               # outer background
        keep.append(f'<path d="{d}" fill="{fill.lower()}" transform="translate({tx:g},{ty:g})"/>')
    return "".join(keep)


def build_original(rgba, info, out_w, out_h, colors, speckle):
    h, w = rgba.shape[:2]
    if info["kind"] == "gradient-shape":
        top, bottom, y0, y1 = info["grad"]
        body = silhouette_svg(info["fg"], "url(#g)", out_w, out_h, speckle=speckle)
        defs = (f'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="{y0}" x2="0" y2="{y1}">'
                f'<stop offset="0" stop-color="{hexc(top)}"/><stop offset="1" stop-color="{hexc(bottom)}"/>'
                f'</linearGradient></defs>')
        i = body.find(">") + 1
        return body[:i] + defs + body[i:]
    paths = trace_original(rgba, info, colors, speckle)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{out_w}" height="{out_h}">'
            f'{paths}</svg>')


def expected_image(rgba, variant):
    """What the variant should look like, as RGB on its check background."""
    _, fg = background(rgba)
    if variant == "original":
        a = rgba[..., 3:4] / 255.0
        return (rgba[..., :3] * a + 255 * (1 - a)).astype(int), "white"
    col, bg = (255, 0) if variant == "white" else (0, 255)
    out = np.full(fg.shape + (3,), bg, int); out[fg] = col
    return out, ("black" if variant == "white" else "white")


def verify(svg_path, rgba_orig, variant):
    h, w = rgba_orig.shape[:2]
    exp, bg = expected_image(rgba_orig, variant)
    got, used = render_to_array(svg_path, w, h, bg=bg)
    if got is None:
        return None, None, None
    diff = float(np.abs(got - exp).mean())
    return round(100 - diff / 255 * 100, 2), used, (exp, got)


def convert_one(path_in, out_dir, variants=None, colors=8, speckle=8, compare=False, icons=False):
    rgba_orig = np.array(Image.open(path_in).convert("RGBA"))
    h0, w0 = rgba_orig.shape[:2]
    rgba = rgba_orig
    if max(w0, h0) < 500:                                 # small image: upscale before tracing
        rgba = np.array(Image.fromarray(rgba_orig).resize((w0 * 3, h0 * 3), Image.LANCZOS))
    info = classify(rgba)
    st = source_type(rgba)
    chosen, notes = normalize_variants(variants or [], st)
    if not variants:
        chosen = ["original"] if st == "color" else ["black"]
    if info["kind"] == "photo":
        notes.append("looks like a photo: result is an approximation and may be large")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path_in))[0]
    report = {"input": path_in, "source_type": st, "method": info["kind"],
              "options": COLOR_OPTIONS if st == "color" else MONO_OPTIONS,
              "variants": {}, "notes": notes}
    for v in chosen:
        if v == "original":
            svg = build_original(rgba, info, w0, h0, colors, speckle)
        else:
            svg = make_variant(rgba, v, w0, h0, speckle=speckle)
        out = os.path.join(out_dir, f"{base}-{v}.svg")
        open(out, "w", encoding="utf-8").write(svg)
        entry = {"file": out}
        sim, used, pair = verify(out, rgba_orig, v)
        if sim is None:
            entry["similarity_pct"] = None
            report.setdefault("notes", []).append("no renderer available: visual check skipped")
        else:
            entry["similarity_pct"] = sim; entry["renderer"] = used
            if compare:
                exp, got = pair
                side = Image.new("RGB", (w0 * 2, h0), "white")
                side.paste(Image.fromarray(exp.astype(np.uint8)), (0, 0))
                side.paste(Image.fromarray(got.astype(np.uint8)), (w0, 0))
                cp = os.path.join(out_dir, f"{base}-{v}_compare.png"); side.save(cp)
                entry["compare"] = cp
        a = audit(out)
        entry["audit"] = {k: a[k] for k in ("verdict", "shapes", "colours", "size_kb", "issues", "notes")}
        report["variants"][v] = entry
    if icons and chosen:
        try:
            files, _ = export_icons(report["variants"][chosen[0]]["file"],
                                    os.path.join(out_dir, "icons"), f"{base}-{chosen[0]}")
            report["icons"] = files
        except RuntimeError as e:
            report["notes"].append(str(e))
    return report


def main():
    ap = argparse.ArgumentParser(description="PNG -> SVG with variants (file or folder)")
    ap.add_argument("inp", help=".png file or folder of .png")
    ap.add_argument("out", nargs="?", help="output folder")
    ap.add_argument("--list-options", action="store_true",
                    help="print the variant checkboxes this image offers, then exit")
    ap.add_argument("--variants", default="",
                    help="comma list from the options (original,white,black) or 'all'")
    ap.add_argument("--colors", type=int, default=8, help="colours for multicolour tracing")
    ap.add_argument("--speckle", type=int, default=8, help="remove spots smaller than this (px)")
    ap.add_argument("--compare", action="store_true", help="save expected-vs-result images")
    ap.add_argument("--icons", action="store_true", help="favicon + app icons from the first variant")
    ap.add_argument("--which-renderers", action="store_true")
    a = ap.parse_args()
    if a.which_renderers:
        print(json.dumps({"renderers": available()})); return
    files = ([os.path.join(a.inp, f) for f in sorted(os.listdir(a.inp)) if f.lower().endswith(".png")]
             if os.path.isdir(a.inp) else [a.inp])
    if a.list_options:
        out = []
        for f in files:
            st = source_type(np.array(Image.open(f).convert("RGBA")))
            out.append({"source": os.path.basename(f), "source_type": st,
                        "options": COLOR_OPTIONS if st == "color" else MONO_OPTIONS,
                        "default": ["original"] if st == "color" else ["black"]})
        print(json.dumps(out[0] if len(out) == 1 else out, indent=2)); return
    if not a.out:
        ap.error("output folder is required (or use --list-options)")
    variants = [v for v in a.variants.split(",") if v.strip()]
    results = []
    for f in files:
        try:
            results.append(convert_one(f, a.out, variants, a.colors, a.speckle, a.compare, a.icons))
        except Exception as e:
            results.append({"input": f, "error": str(e)})
    print(json.dumps(results[0] if len(results) == 1 else results, indent=2))


# kept for older callers: convert(input, output_svg)
def convert(path_in, path_out, colors=8, compare=False):
    rgba = np.array(Image.open(path_in).convert("RGBA"))
    info = classify(rgba)
    h, w = rgba.shape[:2]
    open(path_out, "w", encoding="utf-8").write(build_original(rgba, info, w, h, colors, 8))
    return path_out


if __name__ == "__main__":
    main()
