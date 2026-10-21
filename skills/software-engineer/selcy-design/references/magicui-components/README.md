# Komponen Magic UI — indeks referensi lokal

65 komponen dari Magic UI (MIT, magicui.design), disimpan sebagai JSON di
folder ini. Dipakai oleh skill `pen-design` saat membuat desain yang harus
bisa diimplementasikan (lihat "Design → Code handoff" di SKILL.md).

## Cara baca

Setiap file punya struktur:

```json
{
  "name": "MagicCard",
  "type": "card",
  "description": "A spotlight effect that follows your mouse cursor...",
  "metadata": { "title": "Magic Card", "author": "dillionverma", ... },
  "installation": {
    "pnpm": "pnpm dlx shadcn@latest add \"https://magicui.design/r/magic-card\"",
    "npm": "npx shadcn@latest add \"https://magicui.design/r/magic-card\""
  },
  "props": [...],
  "usage": "..."
}
```

`installation` adalah perintah shadcn CLI resmi — jangan ditulis tangan.

## Kategori (lihat field "type" di tiap file)

- **card**: magic-card, neon-gradient-card, shine-border
- **effect**: meteors, confetti, particles, border-beam, animated-beam
- **text**: aurora-text, number-ticker, typing-animation, word-rotate,
  text-reveal, morphing-text, sparkles-text, kinetic-text
- **background**: grid-pattern, dot-pattern, ripple, retro-grid,
  flickering-grid, hexagon-pattern, light-rays, noise-texture
- **button**: shimmer-button, rainbow-button, ripple-button, pulsating-button
- **device**: android, iphone, safari
- **layout**: bento-grid, marquee, animated-list, dock, file-tree, globe

## Kapan dipakai

- Saat desain memakai efek/animasi yang punya padanan komponen siap pakai,
  sebutkan namanya di spec agar builder tidak menulis efek dari nol.
- Untuk klik "install" tetap gunakan perintah `installation` dari file JSON,
  bukan kode yang diingat.
