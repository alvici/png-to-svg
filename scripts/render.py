"""render: SVG -> PNG with automatic fallback between renderers.

Order tried: cairosvg (Python) -> resvg -> rsvg-convert -> Inkscape -> Chrome/Edge headless.
If none works, render() returns None and the caller should skip visual checks.

Usage:
  python render.py file.svg out.png --width 512 [--height 512] [--bg white]
  python render.py --which        # list renderers available on this computer
"""
import os, sys, shutil, subprocess, tempfile, argparse, glob

IS_WIN = os.name == "nt"


def _find_exe(names, extra_paths=()):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    for pattern in extra_paths:
        for p in glob.glob(os.path.expandvars(pattern)):
            if os.path.isfile(p):
                return p
    return None


def _browser():
    return _find_exe(
        ["msedge", "chrome", "google-chrome", "chromium", "chromium-browser"],
        [
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ],
    )


def _inkscape():
    return _find_exe(["inkscape"], [r"%ProgramFiles%\Inkscape\bin\inkscape.exe",
                                    "/Applications/Inkscape.app/Contents/MacOS/inkscape"])


# ---- backends: each takes (svg_path, png_path, w, h, bg) and raises on failure ----

def _with_bg(svg_path, bg):
    """Return path to an SVG with a solid background rect (for CLI renderers)."""
    if not bg:
        return svg_path
    src = open(svg_path, encoding="utf-8").read()
    i = src.find(">", src.find("<svg")) + 1
    out = src[:i] + f'<rect x="-1e5" y="-1e5" width="2e5" height="2e5" fill="{bg}"/>' + src[i:]
    tmp = tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8")
    tmp.write(out); tmp.close()
    return tmp.name


def b_cairosvg(svg, png, w, h, bg):
    import cairosvg
    cairosvg.svg2png(url=svg, write_to=png, output_width=w, output_height=h, background_color=bg)


def b_resvg(svg, png, w, h, bg):
    exe = _find_exe(["resvg"])
    if not exe: raise RuntimeError("resvg not found")
    subprocess.run([exe, "-w", str(w), "-h", str(h)] + (["--background", bg] if bg else []) + [svg, png],
                   check=True, capture_output=True, timeout=60)


def b_rsvg(svg, png, w, h, bg):
    exe = _find_exe(["rsvg-convert"])
    if not exe: raise RuntimeError("rsvg-convert not found")
    cmd = [exe, "-w", str(w), "-h", str(h), "-o", png] + (["-b", bg] if bg else []) + [svg]
    subprocess.run(cmd, check=True, capture_output=True, timeout=60)


def b_inkscape(svg, png, w, h, bg):
    exe = _inkscape()
    if not exe: raise RuntimeError("Inkscape not found")
    cmd = [exe, svg, "--export-type=png", f"--export-filename={png}", "-w", str(w), "-h", str(h)]
    if bg: cmd += [f"--export-background={bg}", "--export-background-opacity=1"]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)


def b_browser(svg, png, w, h, bg):
    exe = _browser()
    if not exe: raise RuntimeError("Chrome/Edge not found")
    tmpdir = tempfile.mkdtemp()
    try:
        page = os.path.join(tmpdir, "page.html")
        body_bg = bg or "transparent"
        svg_src = open(svg, encoding="utf-8").read()
        svg_src = svg_src[svg_src.find("<svg"):]
        with open(page, "w", encoding="utf-8") as f:
            f.write(f"<!doctype html><html><body style='margin:0;background:{body_bg}'>"
                    f"<div style='width:{w}px;height:{h}px'>"
                    f"<style>svg{{width:{w}px;height:{h}px;display:block}}</style>{svg_src}</div></body></html>")
        shot = os.path.join(tmpdir, "shot.png")
        cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               f"--user-data-dir={os.path.join(tmpdir, 'profile')}",
               f"--window-size={w},{h}", f"--screenshot={shot}"]
        if not bg: cmd.append("--default-background-color=00000000")
        if not IS_WIN and hasattr(os, "geteuid") and os.geteuid() == 0:
            cmd.append("--no-sandbox")
        cmd.append("file:///" + page.replace("\\", "/").lstrip("/"))
        subprocess.run(cmd, check=True, capture_output=True, timeout=90)
        if not os.path.exists(shot): raise RuntimeError("browser produced no screenshot")
        shutil.move(shot, png)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


BACKENDS = [("cairosvg", b_cairosvg), ("resvg", b_resvg), ("rsvg-convert", b_rsvg),
            ("inkscape", b_inkscape), ("browser", b_browser)]


def available():
    out = []
    try:
        import cairosvg  # noqa: F401
        cairosvg.svg2png(bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>')
        out.append("cairosvg")
    except Exception:
        pass
    if _find_exe(["resvg"]): out.append("resvg")
    if _find_exe(["rsvg-convert"]): out.append("rsvg-convert")
    if _inkscape(): out.append("inkscape")
    if _browser(): out.append("browser")
    return out


def render(svg_path, png_path, width, height=None, bg=None, prefer=None):
    """Render svg_path to png_path. Returns the backend name used, or None if all failed."""
    height = height or width
    order = BACKENDS
    if prefer:
        order = sorted(BACKENDS, key=lambda b: b[0] != prefer)
    for name, fn in order:
        src = svg_path if name == "cairosvg" else _with_bg(svg_path, bg) if name != "browser" else svg_path
        try:
            fn(src, png_path, width, height, bg)
            if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                return name
        except Exception:
            continue
        finally:
            if src != svg_path:
                try: os.remove(src)
                except OSError: pass
    return None


def render_to_array(svg_path, width, height=None, bg="white"):
    """Render and return (numpy RGB array, backend) or (None, None)."""
    import numpy as np
    from PIL import Image
    fd, tmp = tempfile.mkstemp(suffix=".png"); os.close(fd)
    try:
        used = render(svg_path, tmp, width, height, bg)
        if not used:
            return None, None
        im = Image.open(tmp).convert("RGBA")
        if im.size != (width, height or width):
            im = im.resize((width, height or width))
        base = Image.new("RGBA", im.size, bg or "white")
        base.alpha_composite(im)
        return np.array(base.convert("RGB")).astype(int), used
    finally:
        try: os.remove(tmp)
        except OSError: pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="SVG -> PNG with renderer fallback")
    ap.add_argument("svg", nargs="?"); ap.add_argument("png", nargs="?")
    ap.add_argument("--width", type=int, default=512); ap.add_argument("--height", type=int)
    ap.add_argument("--bg", default=None, help="background color, default transparent")
    ap.add_argument("--prefer", default=None, help="try this renderer first")
    ap.add_argument("--which", action="store_true", help="list available renderers")
    a = ap.parse_args()
    if a.which or not a.svg:
        print("available renderers:", ", ".join(available()) or "none"); sys.exit(0)
    used = render(a.svg, a.png, a.width, a.height, a.bg, a.prefer)
    if not used:
        print("ERROR: no renderer worked. Install one: pip install cairosvg, or Inkscape, or use Edge/Chrome.")
        sys.exit(1)
    print(f"rendered with {used}: {a.png}")
