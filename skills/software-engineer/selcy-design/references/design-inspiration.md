# Design inspiration — when stuck, look here

Daftar referensi yang **dibuka saat desain**, bukan sekadar dipasang. Tiap
baris menjawab satu pertanyaan: "saya stuck, pola seperti apa yang cocok?"

Tiap baris punya framing problem → buka repo/link → tiru pola, bukan copy
hasil. Jika butuh navigasi cepat, `21st.dev` tidak ada (berbayar,
ditolak maulana 2026-10-20), dan `reactbits` tidak ada (React-only, ditolak).

## Repo yang sudah ada lokal (bisa dibaca langsung)

### awesome-design-md (VoltAgent) — anatomi halaman periodik
Paling berguna saat menemukan tipe halaman baru dan belum mencari ide.
Berisi deskripsi tipe halaman (landing, pricing, dashboard, footer,
testimoni) yang dipecah menjadi blok penyusunnya (hero, CTA, tabel harga,
kartu status, gulir animasi).

kurang lebih `/root/.hermes/profiles/selcy/cache/scratch/design-eval/awesome-design-md`
Buka saat: "saya sedang membuat halaman X, blok penyusun apa saja yang wajib ada?"

### magicui (magicuidesign/magicui) — efek & komponen visual siap pakai
Ships komponen interaktif (kartu sorot penyorot kursor, border bersinar,
nampan marquee, teks animasi, latar pola titik/grid, hujan meteor, dll).
Lisensi MIT. Sudah 65 JSON komponen di folder ini.
Buka saat: "halaman terasa datar, butuh aksen atau satu efek interaktif".
Penanganan lanjutan: lihat `references/magicui-components/<nama>.json` untuk memerintah pemasangan.

### shadcn-ui (shadcn-ui/ui) — basis komponen yang dipakai ribuan proyek
Komponen "kerangka" yang terbuat dengan baik (dialog, dropdown, select,
sidebar, calendar, command palette, chart). Tampilannya sengaja dibuat
tanpa gaya khas agar bisa kustom sesuai tema.
Buka saat: "butuh komponen UI standar (input, modal, navigasi), bukan efek".
Lanjutan: pemasangan melalui MCP shadcn yang terdaftar di `~/.config/opencode/opencode.json`.

### animata (codse/animata) — pola layout + animasi scroll
Kumpulan contoh layout/animasi bergulir (bento grid, daftar kartu, gulir parallax, teks efek reveal).
Buka saat: "gulir halaman terasa statis, butuh pola pengungkapan scroll".

### neobrutalism-components (ekmas) — fallback gaya visual total
Gaya neobrutalisme (tebal, border solid, warna kontras tinggi) sebagai fallback visual saat keputusan desain macet dan butuh gaya yang sengaja "berani" (non-AI-slop).
Buka saat: "tampilan terlalu aman/biasa, butuh gaya yang berkarakter".

### css-button-generator (stepura-v-g) — inventaris tombol
Generator tombol CSS murni (ribuan gaya + source code).
Buka saat: "tombol tidak menonjol, perlu variasi".

## Situs referensi (dibuka saat sedang mencari ide, tidak ada repo)

| Situs | Untuk apa |
| --- | --- |
| motionsites.ai | showcase situs dengan animasi terbaik (buka saat butuh inspirasi gerakan) |
| freefrontend.com/scroll-trigger-js | daftar pola animasi scroll-trigger |
| designprompts.dev | prompt desain + ide konsep |
| ui.aceternity.com | komponen efek (mirip magicui) |
| getdesign.md/design-md | template anatomi halaman periodik |
| designmd-store.com | template mockup siap pakai |
| MDN filter reference | dokumentasi resmi filter CSS (grayscale, blur, dll) |

## Aturan memakai referensi ini

1. Jangan copy-paste kode/hasil mentah — ambil pola strukturnya (urutan blok, gerakan, ritme) dan terapkan dengan token proyek.
2. Wajib tunduk pada pilar kualitas: `antislop*` + `ui-ux-pro-max` (lihat bagian "Pilar kualitas" di SKILL.md utama).
3. Setiap referensi yang dipanggil wajib dicatat di `design/NN-*.md` (referensi yang dipanggil + pola yang diterapkan) agar bisa dditelusuri.
4. Ketika mengambil pola dari repo lokal, baca filament sumbernya (file `.tsx`/`.css`), jangan hanya lihat tampilan akhirnya.
