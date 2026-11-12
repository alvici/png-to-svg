---
name: png-to-svg
description: PNG to SVG — ubah gambar PNG (logo, ikon, ilustrasi datar, line art, bentuk bergradasi) menjadi SVG vektor bersih, satu file atau satu folder, dengan pilihan varian warna (original / white / black) plus favicon dan ikon aplikasi. Pakai saat diminta convert, trace, atau vektorisasi PNG ke SVG.
---

# PNG to SVG

Ubah PNG menjadi SVG vektor sungguhan (path), bukan PNG yang dibungkus SVG.
Semua script ada di folder `scripts/` di samping file ini; jalankan dengan path lengkap.

**Windows:** pakai `python` atau `py -3`, bukan `python3` (sering hanya membuka Microsoft Store).
Persiapan, renderer, dan masalah umum di Windows: `references/windows.md`.

## Langkah kerja

1. **Cek bahan.** Pastikan file PNG bisa dibuka. Jangan mengonversi logo atau karakter
   milik merek lain kecuali pengguna jelas berhak memakainya.

2. **Tanyakan varian.** Jalankan:
   `python scripts/png2svg.py input.png --list-options`
   - `source_type: color` → tawarkan centang: **Original color / White / Black**
   - `source_type: mono`  → tawarkan centang: **Black / White**

   Kalau pengguna sudah menyebut varian, atau tidak bisa ditanya, pakai `default`.
   Detail tiap varian: `references/variants.md`.

3. **Konversi.**
   `python scripts/png2svg.py input.png out_dir --variants original,white,black --compare`
   Tambahkan `--icons` kalau pengguna minta favicon atau ikon aplikasi.
   Untuk satu folder, ganti `input.png` dengan nama folder.

4. **Baca laporan JSON.** Untuk tiap varian ada `similarity_pct` dan `audit`.
   - `similarity_pct` ≥ 97 dan `audit.verdict` = `ok` → selesai.
   - Selain itu, atur ulang `--colors` atau `--speckle` sesuai `references/tuning.md`,
     maksimal 3 kali percobaan.
   - `similarity_pct: null` berarti tidak ada renderer: hasil tetap dibuat, sebutkan bahwa
     pengecekan visual dilewati.
   - Kalau bisa melihat gambar, buka `*_compare.png` (kiri = target, kanan = hasil).

5. **Serahkan.** Berikan file SVG per varian (dan folder `icons/` bila diminta) dengan
   ringkasan pendek: metode, kemiripan, ukuran, dan catatan dari `notes` atau `audit.issues`.

## Aturan

- Jangan pernah mengubah file asli; selalu tulis ke folder output.
- Varian white/black adalah siluet satu warna. Detail beda warna di dalam bentuk ikut
  menyatu; sebutkan ke pengguna kalau logonya punya detail seperti itu.
- Script tambahan: `scripts/svg_audit.py` (audit SVG mana pun), `scripts/render.py --which`
  (cek renderer yang tersedia), `scripts/variants.py` (varian dari SVG yang sudah ada).
- Integrasi checkbox di dashboard AION: `references/aion-integration.md`.
