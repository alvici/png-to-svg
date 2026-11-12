# Varian warna

## Pilihan per jenis sumber

| Sumber | Deteksi | Pilihan centang | Default |
|---|---|---|---|
| Berwarna | >5% piksel latar depan punya saturasi (selisih kanal >40) | Original color, White, Black | Original color |
| Hitam-putih / abu-abu | selain itu | Black, White | Black |

Kalau pengguna meminta `original` untuk sumber hitam-putih, script menggantinya dengan `black`
dan menulis catatan di `notes`.

## Isi tiap varian

- **original**: warna asli, latar dibuang (transparan). Bentuk bergradasi vertikal dibuat
  sebagai satu path dengan `linearGradient`; lainnya hasil tracing warna.
- **black**: siluet hitam `#000000` untuk latar terang. Lubang di dalam bentuk tetap transparan.
- **white**: siluet putih `#ffffff` untuk latar gelap. Pengecekan dirender di atas latar hitam.

Nama file: `<nama>-original.svg`, `<nama>-white.svg`, `<nama>-black.svg`.

## Ikon (`--icons`)

Dibuat dari varian pertama yang dipilih, di kanvas persegi dengan sedikit padding:
PNG 16, 32, 48, 180 (Apple touch), 192, 512 (PWA/app) dan `favicon.ico` (16/32/48),
semuanya berlatar transparan, di folder `out_dir/icons/`.

## Batasan

- Varian white/black menyatukan semua bagian latar depan. Elemen beda warna yang saling
  bersentuhan (misalnya segitiga kuning di atas kotak hijau) tidak lagi terpisah.
- Varian dari SVG yang sudah ada (`variants.py logo.svg ...`) butuh renderer, karena SVG
  dirender dulu lalu ditelusuri ulang. Kalau PNG asli ada, lebih baik pakai PNG.
