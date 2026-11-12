"""variants: colour variants (original / white / black) and favicon / app-icon export.

Rules:
  - colour source        -> options: original, white, black
  - black & white source -> options: black, white

Usage:
  python variants.py input.png --list-options            # JSON for checkboxes (AION UI)
  python variants.py input.png out_dir --variants white,black [--icons]
  python variants.py logo.svg  out_dir --variants black      # SVG input works too (needs a renderer)
"""
import os, re, io, json, argparse, tempfile
import numpy as np
from PIL import Image
import vtracer

COLOR_OPTIONS = ["original", "white", "black"]
MONO_OPTIONS = ["black", "white"]
FILL = {"white": "#ffffff", "black": "#000000"}
ICON_SIZES = [16, 32, 48, 180, 192, 512]


# ---------------- image analysis shared with png2svg ----------------

def load_rgba(path):
    """Open PNG (or render SVG) and return RGBA numpy array."""
    if path.lower().endswith(".svg"):
        from render import render
        fd, tmp = tempfile.mkstemp(suffix=".png"); os.close(fd)
        try:
            w, h = svg_size(path)
            scale = max(1, 1000 // max(w, h))
            if not render(path, tmp, int(w * scale), int(h * scale), bg=None):
                raise RuntimeError("cannot render SVG input: no renderer available")
            return np.array(Image.open(tmp).convert("RGBA"))
        finally:
            try: os.remove(tmp)
            except OSError: pass
    return np.array(Image.open(path).convert("RGBA"))


def background(rgba):
    """Return (bg_rgb or None if transparent, foreground mask)."""
    alpha = rgba[..., 3]
    rgb = rgba[..., :3].astype(int)
    if (alpha < 128).mean() > 0.02:              # real transparency present
        return None, alpha >= 128
    corners = [tuple(rgb[0, 0]), tuple(rgb[0, -1]), tuple(rgb[-1, 0]), tuple(rgb[-1, -1])]
    bg = max(set(corners), key=corners.count)
    return bg, np.abs(rgb - np.array(bg)).sum(-1) > 60


def source_type(rgba):
    """'color' if the foreground has real colour, 'mono' if black/white/grey only."""
    bg, fg = background(rgba)
    if not fg.any():
        return "mono"
    rgb = rgba[..., :3].astype(int)[fg]
    sat = rgb.max(1) - rgb.min(1)
    return "color" if (sat > 40).mean() > 0.05 else "mono"


def options_for(path):
    st = source_type(load_rgba(path))
    return {"source": os.path.basename(path), "source_type": st,
            "options": COLOR_OPTIONS if st == "color" else MONO_OPTIONS,
            "default": ["original"] if st == "color" else ["black"]}


def normalize_variants(requested, st):
    """Map user choices to what the source supports; returns (list, notes)."""
    allowed = COLOR_OPTIONS if st == "color" else MONO_OPTIONS
    if not requested or requested == ["all"]:
        return list(allowed), []
    out, notes = [], []
    for v in requested:
        v = v.strip().lower()
        if v not in allowed:
            if v == "original" and st == "mono":
                notes.append("source is black & white: 'original' replaced by 'black'")
                v = "black"
            else:
                notes.append(f"unknown variant '{v}' skipped"); continue
        if v not in out:
            out.append(v)
    return out, notes


# ---------------- tracing a single-colour silhouette ----------------

def trace_mask(mask, speckle=8):
    """Trace a boolean mask -> list of (d, tx, ty)."""
    m = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8)).convert("RGB")
    buf = io.BytesIO(); m.save(buf, "PNG")
    svg = vtracer.convert_raw_image_to_svg(
        buf.getvalue(), img_format="png", colormode="binary", mode="spline",
        filter_speckle=speckle, corner_threshold=60, length_threshold=4.0,
        splice_threshold=45, path_precision=2)
    found = re.findall(r'<path d="([^"]+)"[^>]*transform="translate\(([-\d.]+),([-\d.]+)\)"', svg)
    return found or [(d, "0", "0") for d in re.findall(r'<path d="([^"]+)"', svg)]


def silhouette_svg(mask, fill, out_w, out_h, scale=1, speckle=8):
    paths = trace_mask(mask, speckle)
    body = "".join(f'<path d="{d}" transform="translate({tx},{ty})"/>' for d, tx, ty in paths)
    h, w = mask.shape
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{out_w}" height="{out_h}">'
            f'<g fill="{fill}" fill-rule="evenodd">{body}</g></svg>')


def make_variant(rgba, variant, out_w, out_h, scale=1, speckle=8):
    """White/black variant from the foreground silhouette (holes stay transparent)."""
    _, fg = background(rgba)
    return silhouette_svg(fg, FILL[variant], out_w, out_h, scale, speckle)


# ---------------- favicon / app icons ----------------

def svg_size(path):
    src = open(path, encoding="utf-8").read()
    m = re.search(r'viewBox="\s*([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)', src)
    if m:
        return float(m.group(3)), float(m.group(4))
    w = re.search(r'width="([\d.]+)', src); h = re.search(r'height="([\d.]+)', src)
    return float(w.group(1)), float(h.group(1))


def square_svg(path, padding=0.06):
    """Copy of the SVG on a square canvas with padding (so icons are centred, not stretched)."""
    src = open(path, encoding="utf-8").read()
    m = re.search(r'viewBox="\s*([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)\s*"', src)
    x, y, w, h = [float(v) for v in m.groups()] if m else (0, 0, *svg_size(path))
    side = max(w, h) * (1 + 2 * padding)
    nx, ny = x - (side - w) / 2, y - (side - h) / 2
    tag_end = src.find(">", src.find("<svg"))
    head = src[src.find("<svg"):tag_end]
    head = re.sub(r'\s(viewBox|width|height)="[^"]*"', "", head)
    head += f' viewBox="{nx:.2f} {ny:.2f} {side:.2f} {side:.2f}" width="512" height="512"'
    return head + src[tag_end:]


def export_icons(svg_path, out_dir, prefix):
    """PNG icons at ICON_SIZES + favicon.ico (16/32/48). Returns list of files or raises."""
    from render import render
    os.makedirs(out_dir, exist_ok=True)
    fd, sq = tempfile.mkstemp(suffix=".svg"); os.close(fd)
    open(sq, "w", encoding="utf-8").write(square_svg(svg_path))
    files, ico_imgs, used = [], [], None
    try:
        for s in ICON_SIZES:
            p = os.path.join(out_dir, f"{prefix}-{s}.png")
            used = render(sq, p, s, s, bg=None)
            if not used:
                raise RuntimeError("no renderer available for icons (install cairosvg, Inkscape, or use Edge/Chrome)")
            files.append(p)
            if s in (16, 32, 48):
                ico_imgs.append(Image.open(p).convert("RGBA"))
        ico = os.path.join(out_dir, f"{prefix}-favicon.ico")
        big = Image.open(os.path.join(out_dir, f"{prefix}-48.png")).convert("RGBA")
        big.save(ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
        files.append(ico)
    finally:
        os.remove(sq)
    return files, used


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Colour variants + icons")
    ap.add_argument("inp", help="source .png (best) or .svg")
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--list-options", action="store_true", help="print the checkbox options for this source")
    ap.add_argument("--variants", default="", help="comma list: original,white,black or 'all'")
    ap.add_argument("--icons", action="store_true", help="also export favicon + app icons from the first variant")
    a = ap.parse_args()
    if a.list_options or not a.out_dir:
        print(json.dumps(options_for(a.inp), indent=2)); raise SystemExit
    rgba = load_rgba(a.inp)
    st = source_type(rgba)
    chosen, notes = normalize_variants([v for v in a.variants.split(",") if v], st)
    os.makedirs(a.out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(a.inp))[0]
    h, w = rgba.shape[:2]
    result = {"source_type": st, "variants": {}, "notes": notes}
    for v in chosen:
        out = os.path.join(a.out_dir, f"{base}-{v}.svg")
        if v == "original":
            from png2svg import convert
            convert(a.inp, out)
        else:
            open(out, "w", encoding="utf-8").write(make_variant(rgba, v, w, h))
        result["variants"][v] = out
    if a.icons and chosen:
        first = result["variants"][chosen[0]]
        result["icons"], _ = export_icons(first, os.path.join(a.out_dir, "icons"), f"{base}-{chosen[0]}")
    print(json.dumps(result, indent=2))
