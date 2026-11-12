# Integrasi dengan dashboard AION

Script ini bisa dipanggil langsung dari server Node/Express AION tanpa lewat agen.

## 1. Ambil pilihan checkbox

```
py -3 scripts/png2svg.py upload.png --list-options
```
Output:
```json
{"source": "upload.png", "source_type": "color",
 "options": ["original", "white", "black"], "default": ["original"]}
```
Tampilkan satu checkbox per item di `options`; centang awal sesuai `default`.
Label: original → "Original color", white → "White", black → "Black".

## 2. Jalankan konversi dengan pilihan pengguna

```
py -3 scripts/png2svg.py upload.png out_dir --variants white,black [--icons]
```
Hasil di stdout berupa JSON: `variants.<nama>.file`, `similarity_pct`, `audit`,
dan `icons` (daftar file) bila diminta.

## Contoh pemanggilan dari Node

```js
const { execFile } = require("child_process");
const py = process.platform === "win32" ? "py" : "python3";
const pre = process.platform === "win32" ? ["-3"] : [];
function png2svg(args) {
  return new Promise((resolve, reject) =>
    execFile(py, [...pre, "scripts/png2svg.py", ...args],
      { cwd: SKILL_DIR, maxBuffer: 10 * 1024 * 1024 },
      (err, out) => (err ? reject(err) : resolve(JSON.parse(out)))));
}
// const opts = await png2svg([file, "--list-options"]);
// const res  = await png2svg([file, outDir, "--variants", chosen.join(","), "--icons"]);
```
