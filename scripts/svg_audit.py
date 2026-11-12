"""svg_audit: check an SVG produced by png2svg for quality problems.

Checks: viewBox, size, path count, node count, colours, tiny fragments, embedded
rasters, live text, filters/masks, number precision. Prints JSON with a verdict.

Usage:
  python svg_audit.py file.svg [--json]
"""
import re, os, sys, json, argparse
import xml.etree.ElementTree as ET

NUM = re.compile(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?")
CMD = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")


def _local(tag):
    return tag.split("}", 1)[-1]


def _viewbox(root):
    vb = root.get("viewBox")
    if vb:
        v = [float(x) for x in NUM.findall(vb)]
        if len(v) == 4:
            return v
    try:
        w = float(NUM.findall(root.get("width", ""))[0]); h = float(NUM.findall(root.get("height", ""))[0])
        return [0, 0, w, h]
    except (IndexError, ValueError):
        return None


def _translate(el):
    m = re.search(r"translate\(\s*([-\d.eE]+)[ ,]+([-\d.eE]+)", el.get("transform", ""))
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)


def _subpath_boxes(d, tx, ty):
    """Approximate bounding boxes of each subpath (absolute commands assumed, as vtracer writes)."""
    boxes = []
    for part in re.split(r"(?=[Mm])", d):
        nums = [float(n) for n in NUM.findall(part)]
        if len(nums) < 4:
            continue
        xs = nums[0::2]; ys = nums[1::2]
        boxes.append((min(xs) + tx, min(ys) + ty, max(xs) + tx, max(ys) + ty))
    return boxes


def _fill(el, inherited):
    f = el.get("fill")
    st = el.get("style", "")
    m = re.search(r"fill\s*:\s*([^;]+)", st)
    if m: f = m.group(1).strip()
    return f if f else inherited


def audit(path):
    raw = open(path, encoding="utf-8").read()
    issues, notes = [], []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        return {"file": path, "verdict": "fail", "issues": [f"invalid XML: {e}"]}

    vb = _viewbox(root)
    if not root.get("viewBox"):
        issues.append("no viewBox: the SVG will not scale cleanly")
    area = (vb[2] * vb[3]) if vb else None

    paths, colours, nodes, tiny, decimals = 0, set(), 0, 0, 0
    gradients = rasters = texts = filters = 0

    def walk(el, inherited_fill):
        nonlocal paths, nodes, tiny, decimals, gradients, rasters, texts, filters
        tag = _local(el.tag)
        fill = _fill(el, inherited_fill)
        if tag in ("linearGradient", "radialGradient"):
            gradients += 1
        elif tag == "image":
            rasters += 1
        elif tag in ("text", "tspan"):
            texts += 1
        elif tag in ("filter", "mask"):
            filters += 1
        elif tag == "stop":
            c = el.get("stop-color")
            if c: colours.add(c.lower())
        elif tag in ("path", "rect", "circle", "ellipse", "polygon", "polyline"):
            paths += 1
            if fill and fill != "none" and not fill.startswith("url("):
                colours.add(fill.lower())
            if tag == "path":
                d = el.get("d", "")
                nodes += len(CMD.findall(d))
                for n in NUM.findall(d):
                    if "." in n and len(n.split(".")[1]) > 3:
                        decimals += 1
                if area:
                    tx, ty = _translate(el)
                    for x0, y0, x1, y1 in _subpath_boxes(d, tx, ty):
                        if (x1 - x0) * (y1 - y0) < area * 0.00002:
                            tiny += 1
        for ch in el:
            walk(ch, fill)

    walk(root, root.get("fill"))

    size_kb = round(os.path.getsize(path) / 1024, 1)
    if rasters: issues.append(f"{rasters} embedded raster image(s): not a true vector")
    if texts: notes.append(f"{texts} live text element(s): font may differ on other computers")
    if filters: notes.append(f"{filters} filter/mask element(s): may render differently between apps")
    if paths == 0: issues.append("no shapes found")
    if paths > 300: issues.append(f"{paths} shapes: too many, try fewer colours (--colors)")
    elif paths > 80: notes.append(f"{paths} shapes: on the heavy side for a logo/icon")
    if nodes > 8000: issues.append(f"{nodes} path commands: very complex, try a higher --speckle or fewer colours")
    elif nodes > 3000: notes.append(f"{nodes} path commands: fairly complex")
    if len(colours) > 24: issues.append(f"{len(colours)} colours: looks like a photo or noisy trace")
    elif len(colours) > 12: notes.append(f"{len(colours)} colours: more than a typical logo")
    if tiny > 20: issues.append(f"{tiny} tiny fragments (speckles): raise --speckle")
    elif tiny > 5: notes.append(f"{tiny} tiny fragments")
    if decimals > 200: notes.append("long decimals in path data: file could be smaller")
    if size_kb > 500: issues.append(f"{size_kb} KB: large for a vector logo")
    elif size_kb > 150: notes.append(f"{size_kb} KB: on the large side")

    verdict = "fail" if any(s.startswith(("no shapes", "invalid")) for s in issues) else \
              "warn" if issues else "ok"
    return {"file": path, "verdict": verdict, "viewBox": vb, "size_kb": size_kb, "shapes": paths,
            "path_commands": nodes, "colours": len(colours), "gradients": gradients,
            "tiny_fragments": tiny, "issues": issues, "notes": notes}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Audit an SVG")
    ap.add_argument("svg", nargs="+")
    a = ap.parse_args()
    res = [audit(p) for p in a.svg]
    print(json.dumps(res[0] if len(res) == 1 else res, indent=2))
    sys.exit(1 if any(r["verdict"] == "fail" for r in res) else 0)
