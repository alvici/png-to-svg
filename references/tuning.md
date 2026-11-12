# Metode dan cara memperbaiki hasil

## Metode yang dipilih otomatis (`method` di laporan)

| method | Artinya | Cara tracing |
|---|---|---|
| gradient-shape | satu bentuk dengan gradasi vertikal | siluet + `linearGradient` (1 path) |
| flat | ≤4 kelompok warna | tracing warna |
| multicolor | 5–64 kelompok warna | warna dikurangi ke `--colors`, lalu tracing |
| photo | lebih dari itu | tetap dicoba; beri tahu pengguna hasilnya hanya perkiraan |

Gambar di bawah 500 px diperbesar 3× sebelum tracing.

## Memperbaiki hasil

| Gejala (dari laporan) | Coba |
|---|---|
| similarity < 97, warna hilang / tergabung | naikkan `--colors` (8 → 12 → 16) |
| shapes / path_commands terlalu banyak, file besar | turunkan `--colors` (8 → 6 → 4) |
| `tiny fragments` banyak, bintik-bintik | naikkan `--speckle` (8 → 16 → 24) |
| detail kecil yang penting hilang | turunkan `--speckle` (8 → 4) |
| method `photo` pada logo | turunkan `--colors` ke 4–6; cek apakah PNG-nya buram/terkompresi |
| gradasi horizontal/radial jadi pita warna | belum didukung khusus; naikkan `--colors` dan beri tahu pengguna |

Maksimal 3 percobaan; setelah itu serahkan hasil terbaik beserta catatannya.

## Audit (`svg_audit.py`)

Memeriksa: viewBox ada, jumlah bentuk, jumlah perintah path, jumlah warna, fragmen kecil,
gambar raster tertanam, teks, filter/mask, panjang desimal, ukuran file.
`verdict`: `ok`, `warn` (ada `issues`), atau `fail` (XML rusak / tidak ada bentuk).
`notes` hanya informasi, bukan kesalahan.
