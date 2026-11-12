# PNG to SVG

An AI skill that converts PNG images into genuine, editable SVG vector artwork—not just a PNG embedded inside an SVG file.

It is designed for logos, icons, flat illustrations, line art, and images with gradients. Convert a single image or process a whole folder, create color variants, and optionally generate favicon and app icons.

## Features

- Trace PNG artwork into SVG paths.
- Create original-color, white-silhouette, or black-silhouette variants.
- Process one PNG or a folder of images.
- Render and compare output against the source when a renderer is available.
- Audit SVG files and report potential quality issues.
- Optionally generate favicon and app icon files.

## Repository contents

- `SKILL.md` — instructions for AI agents using this skill.
- `scripts/png2svg.py` — main PNG-to-SVG conversion workflow.
- `scripts/render.py` — renderer detection and image rendering.
- `scripts/svg_audit.py` — SVG quality auditing.
- `scripts/variants.py` — create variants from existing SVG files.
- `references/` — usage guidance, tuning, Windows setup, and AION integration notes.
- `requirements.txt` — Python dependencies.

## Requirements

- Python 3.
- Install the Python dependencies:

  ```bash
  pip install -r requirements.txt
  ```

On Windows, use `python` or `py -3` in place of `python3`. See [`references/windows.md`](references/windows.md) for setup and troubleshooting details.

## Usage

Run commands from the repository directory. Replace `input.png` and `out_dir` with your image path and desired output folder.

List the available variants for an image:

```bash
python scripts/png2svg.py input.png --list-options
```

Convert an image into selected variants and generate comparison images where possible:

```bash
python scripts/png2svg.py input.png out_dir --variants original,white,black --compare
```

Convert all PNGs in a folder:

```bash
python scripts/png2svg.py path/to/images out_dir --variants original
```

Add `--icons` if you also want favicon and app icon outputs. For all supported options, run:

```bash
python scripts/png2svg.py --help
```

## Quality checks

The conversion report includes similarity and SVG audit information. Visual comparison depends on an available renderer; see [`references/windows.md`](references/windows.md) for renderer setup. You can also audit an SVG directly:

```bash
python scripts/svg_audit.py path/to/image.svg
```

## Notes

- The source image is not modified; outputs are written to the chosen output folder.
- White and black variants are single-color silhouettes, so internal color details may merge.
- Only convert artwork you own or are authorized to use.

## License

See the [`LICENSE`](LICENSE) file for the terms that apply to this repository.
