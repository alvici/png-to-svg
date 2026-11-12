# Windows

## Perintah Python

Pakai `python` atau `py -3`. Di banyak PC Windows, `python3` hanya membuka Microsoft Store.

```
cd C:\Users\<nama>\AION-Workspaces\skills\png-to-svg
py -3 -m pip install -r requirements.txt
py -3 scripts\png2svg.py C:\path\logo.png C:\path\hasil --list-options
```

Path dengan spasi diberi tanda kutip: `"C:\My Logos\logo.png"`.

## Renderer (untuk pengecekan visual dan ikon)

`scripts/render.py` mencoba berurutan dan memakai yang pertama berhasil:

1. **cairosvg** (Python). Sering gagal di Windows karena library Cairo tidak ada.
2. **resvg** (`resvg.exe` di PATH).
3. **rsvg-convert**.
4. **Inkscape** (dicari juga di `C:\Program Files\Inkscape\bin`).
5. **Microsoft Edge / Chrome** headless. Edge sudah terpasang di Windows 10/11, jadi ini
   biasanya tetap jalan walau yang lain gagal.

Cek yang tersedia: `py -3 scripts\render.py --which`.
Kalau tidak ada satu pun, konversi tetap berjalan; hanya pengecekan visual dan ikon dilewati.

## Masalah umum

| Pesan | Penyebab | Solusi |
|---|---|---|
| `no library called "cairo"` | Cairo tidak ada | abaikan (fallback jalan) atau install Inkscape |
| `ModuleNotFoundError: vtracer` | belum install | `py -3 -m pip install -r requirements.txt` |
| `python3` membuka Store | stub Windows | pakai `py -3` |
| renderer `browser` lambat | Edge dibuka per gambar | wajar; untuk batch besar install Inkscape atau resvg |
