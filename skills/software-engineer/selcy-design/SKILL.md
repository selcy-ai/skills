---
name: selcy-design
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion
description: "Run /selcy-design before /selcy-implement for any feature whose spec carries a ## Design Reference. Appends the feature's screens as frames in the project's single .pen file (never one file per page), resolves cross-frame inconsistencies before they reach the builder, exports html-tailwind or html-css plus PNG, and writes design/NN-name.md naming frame ids and tokens. Pair worker with /selcy-implement for UI."
---

# selcy-design — design worker for the SELCy loop

The design half of a feature. `/selcy-sdd` writes the spec; this skill
makes the mockup the spec references; `/selcy-implement` builds from both.
Design happens **per feature, inside the loop** — never all screens upfront,
because a mockup built before any build feedback goes stale the moment a
later feature changes the data model.

## When this skill runs

Only when the feature spec carries a `## Design Reference` section. If it
does not, the feature needs no mockup and this skill is not invoked. The
orchestrator decides: it reads the spec, sees the section, and delegates
`/selcy-design NN` before `/selcy-implement NN`.

One feature per run, same rule as the builder. Never design two features in
one chat — a mistake in one must not reach the other.

## Inputs it reads

1. `context/feature-specs/NN-name.md` — the `## Design Reference` section
   names: the screens this feature needs, the breakpoints (desktop 1360,
   mobile 390, tablet 820 only when the spec asks), and any component from
   the ready-made library (see `references/` below).
2. `context/ui-context.md` — the design system: colors, typography, radius,
   component conventions. If the project has done a design kickoff, the
   tokens live here and in the `.pen` file's variables.
3. The project's single `.pen` file (path named in `ui-context.md`, default
   `design/<project>.pen`) — appended to, never replaced.
4. Prior `design/NN-*.md` notes — for consistency with screens already
   designed, not for re-reading the whole history.

## The single .pen rule

**One product = one `.pen` file.** All screens of all features live as
frames in that one file. Never create `dashboard.pen`, `report-form.pen`,
`settings.pen` — that fragments the design system and the engineer loses
the overview. The example to follow is `cek.pen`: 32 desktop frames
(1360px), 32 mobile frames (390px), 3 tablet frames (820px), one file.

Frame naming, in story order:

- `00 · Panduan desain & peta halaman` — frame pertama: ringkasan produk +
  daftar semua frame. **Updated every run** to stay the index of the file.
- `01 · <nama halaman>` … `29 · <nama>` — desktop, 1360px
- `M01 · Mobile · <nama>` … `M29 ·` — mobile, 390px
- `T02 · Tablet · <nama>` — tablet, 820px, only for key screens the spec names
- `30 · Komponen & spesifikasi interaksi`, `31 · Navigasi mobile` — katalog,
  diisi saat ada komponen reusable baru

Numbers come from the feature's checkpoint/feature number where possible so
a frame is traceable to the spec that ordered it. Frames from other
features are never renamed or renumbered — the same stability rule as
feature specs.

## Quality bar — the rules this skill must apply

Desain harus terasa dibuat desainer, bukan digenerate AI. Sebelum membuat
apapun, muat dan terapkan aturan dari skill-skill ini (sudah terpasang di
profile ini):

- **`antislop`** — aturan inti anti AI-slop (10 aturan kualitas). Wajib.
- **`antislop-ui`** — layout/visual halaman web
- **`antislop-layoutmobile`** — layout mobile (saat membuat frame 390px)
- **`antislop-copywriting`** — microcopy, label tombol, teks kosong
- **`ui-ux-pro-max`** — panduan terstruktur: aksesibilitas (kontras 4.5:1),
  touch target (44px+), palet produk, pasangan font, animasi, responsive.
  Query via `scripts/search.py --domain <style|color|chart|ux|typography|gsap> "<query>"`

Dan **cek referensi komponen siap pakai** di
`references/magicui-components/` (65 komponen Magic UI dengan perintah
install resmi `npx shadcn@latest add "https://magicui.design/r/<nama>"`).
Saat desain memakai efek/animasi, prioritaskan yang sudah ada — builder
tidak perlu menulis efek dari nol. Sebutkan nama komponennya di
`design/NN-*.md` kalau dipakai.

## Stuck? Open the inspiration shelf, do not freestyle

Saat bingung pilihan desain (layout, ritme, gerakan, atau gaya visual
secara keseluruhan), buka `references/design-inspiration.md`. File itu
memetakan sumber-sumber ini ke pertanyaan desain konkret:

- **awesome-design-md** — anatomi halaman periodik: blok penyusun landing,
  pricing, dashboard, footer, testimoni. Untuk "halaman tipe X isinya apa
  saja?"
- **magicui** (repo lokal) — efek & komponen visual siap pakai
- **shadcn-ui** (repo lokal) — komponen kerangka standar (dialog, select,
  sidebar, command palette)
- **animata** (repo lokal) — pola layout + animasi scroll (bento grid,
  parallax, reveal)
- **neobrutalism-components** (repo lokal) — fallback gaya visual total saat
  tampilan terlalu aman
- **css-button-generator** (repo lokal) — inventaris tombol
- **motionsites.ai, freefrontend/scroll-trigger-js, designprompts.dev,
  aceternity, designmd-store, getdesign.md** — situs showcase, buka saat
  mencari ide

Lokasi repo lokal: `/root/.hermes/profiles/selcy/cache/design-refs/<nama>`.
Aturan pakai: **tiru pola, bukan copy hasil** — urutan blok, gerakan, ritme
— dan tetap tunduk quality bar di atas. Setiap referensi yang dipanggil
wajib dicatat di `design/NN-*.md` (sumber + pola yang diambil), agar
tertelusuri dan engineer tahu dari mana suatu keputusan desain berasal.

## The tool: pen.dev CLI

Models change; the contract does not. Use whatever provider the project
state names. On this host the working invocation is:

```bash
cd <project-design-dir> && pen --out design/<project>.pen \
  --agent pen.dev --model 'pi;pen.dev;accounts/fireworks/models/minimax-m3' \
  -p "<prompt>" --export design/<NN>-preview.png --export-scale 2
```

Notes specific to this host (verified 2026-10-20):

- `--model omniroute/...` and `--agent omniroute` are **not** accepted by
  the CLI even though `~/.pencil/models.json` lists the omniroute provider.
  `--agent pen.dev` with a `pi;pen.dev;...` model id works with the stored
  pen.dev session.
- `pen --prompt-file/-f` requires `-p` to also be present (attachment, not
  a prompt loader). Put the prompt in `-p` directly.
- Iteration uses `--in file.pen --out file.pen` — frames not mentioned in
  the prompt are left alone.

### Multi-frame prompt (mandatory)

The prompt must state the single-file multi-frame contract explicitly,
otherwise pen.dev makes one frame per file. Template:

```
Buat desain UI untuk <fitur> dari aplikasi <produk>. Semua halaman dibuat
sebagai frame terpisah di dalam file .pen ini (jangan satu file per
halaman): frame <NN> · <nama> desktop 1360px berisi <isi>, frame M<NN> ·
Mobile · <nama> 390px <penyesuaian mobile>. Gaya: <token dari ui-context.md>.
Pertahankan konsistensi dengan frame yang sudah ada di file ini.
```

### Inconsistencies must be resolved here, not in the build

Mockup frames that disagree with each other are the single biggest source
of implementation drift (field Alamat digambarkan sebagai kotak kosong di
frame desktop tetapi input berisi di frame mobile — builder ambil keputusan
sendiri, hasilnya menyimpang). Aturan:

- **Satu frame per breakpoint adalah sumber kebenaran.** State mana yang
  benar dipilih di sini, saat desain dibuat, dan perbedaan antar-frame
  disengaja (responsive) atau diperbaiki (error).
- Setiap perbedaan yang disengaja (misalnya chip status berbaris di mobile,
  berekolom di desktop) **ditulis di `design/NN-*.md`** dengan alasannya.
- Jika mockup tidak bisa menunjukkan sebuah state (loading, error, kosong),
  tandai sebagai kosong — builder mengambilnya dari `ui-context.md`.

## Export — the handoff artifacts

Setelah frame final, export **dua** hal (PNG untuk manusia, HTML untuk
builder):

```bash
# 1. Ambil frame id dari struktur .pen (JSON)
python3 -c "import json; d=json.load(open('design/<project>.pen')); [print(c['id'], c.get('width'), c['name'][:50]) for c in d['children']]"

# 2. Export HTML — pilih format sesuai stack implementasi
printf 'execute({ input: "Export([\"<id1>\",\"<id2>\"], \"html-tailwind\", \"design/<project>-ref.html\")" })\nexit()\n' \
  | pen interactive -i design/<project>.pen -o design/<project>.pen
```

- **`html-tailwind`** saat app memakai Tailwind. Output: class Tailwind
  arbitrary-value + `data-pencil-name` per layer.
- **`html-css`** saat app memakai CSS murni / CSS Modules. Struktur DOM
  sama, style terpisah.

`Export` multi-frame menghasilkan **satu file HTML** berisi semua frame
yang dipilih. Pilih hanya frame milik fitur ini — export semua frame
sekaligus akan menolak urutan terlalu panjang. Catatan: `export-type` CLI
flag hanya mendukung png/jpeg/webp/pdf; HTML harus lewat `Export` di
interactive mode.

## Output: `design/NN-<nama>.md`

Setiap run menulis satu file note, minimal berisi:

- **Frame index**: frame id + nama + breakpoint yang dibuat run ini
- **Token yang dipakai**: warna (hex), font, radius — disalin dari
  `ui-context.md` atau diumumkan kalau baru (lalu `ui-context.md`
  diperbarui lewat `/selcy-sync`, bukan di sini diam-diam)
- **Keputusan inkonsistensi**: perbedaan antar-frame yang disengaja +
  alasan (misalnya "chip status kolom di desktop, baris di mobile —
  mengikuti frame M02")
- **Komponen siap pakai**: nama komponen magicui/shadcn yang dipakai +
  perintah install
- **State yang tidak digambarkan**: loading/error/empty — dari mana
  (ui-context.md default)

File ini adalah apa yang `/selcy-implement` baca sebagai kontrak visual,
bersama `-ref.html`.

## Execution

### Step 0: Route

- Spec punya `## Design Reference`? Tidak → stop, feature ini tidak butuh
  desain. Ya → lanjut.
- `.pen` produk tidak ada → ini run pertama: jalankan **design kickoff**
  (lihat bawah), bukan desain fitur.
- `.pen` ada → desain fitur (Step 1).

### Step 1: Design kickoff (sekali per proyek)

Sekali, setelah `/selcy-sdd` selesai dan sebelum fitur UI pertama:

1. Baca `context/ui-context.md` — ambil token (warna, font, radius) sebagai
   variabel di `.pen` (lewat `SetVariables` di interactive mode atau minta
   di prompt kickoff).
2. Buat `.pen` produk dengan frame `00 · Panduan` + shell navigasi (header,
   sidebar, bottom-nav mobile) + frame `30 · Komponen` katalog komponen
   dasar (tombol, input, badge, card) sesuai token.
3. Export PNG kickoff, kirim ke engineer untuk persetujuan **sebelum**
   fitur pertama dibangun. Design system adalah kontrak; mengubahnya
   setelah 10 frame ada adalah pekerjaan besar.
4. Tulis `design/00-kickoff.md`.

### Step 2: Design the feature

1. Baca spec + `ui-context.md` + frame yang sudah ada di `.pen` (konsistensi).
2. Terapkan quality bar (`antislop*`, `ui-ux-pro-max`, cek referensi
   komponen).
3. Generate dengan prompt multi-frame, iterate dengan `--in/--out` sampai
   frames ini benar.
4. **Verifikasi inkonsistensi**: buka render PNG per frame, bandingkan
   field/komponen yang sama antar breakpoint. Resolve sebelum export.
5. Export PNG per frame + `-ref.html` (html-tailwind/html-css sesuai stack).
6. Update frame `00 · Panduan` agar tetap menjadi indeks yang akurat.

### Step 3: Write the note

Tulis `design/NN-<nama>.md` (lihat format di atas). Update
`progress-tracker.md` satu baris: feature NN designed, artifacts at
`design/NN-*.md` + `-ref.html`.

### Step 4: Handoff

Kirim PNG + `.pen` + `-ref.html` ke engineer (MEDIA: paths, satu per baris).
Lapor: frame apa yang dibuat, keputusan inkonsistensi apa yang diambil,
komponen siap pakai apa yang dipakai, dan tidak ada langkah verifikasi yang
dilewati. Next step selalu: `/selcy-implement NN` di chat baru.

## What this skill never does

- Never membuat file `.pen` per halaman — satu produk, satu file.
- Never melanjutkan saat frame kontradiktif — resolve di sini, bukan di build.
- Never mengABAIKAN quality bar (antislop, aksesibilitas, touch target).
- Never mengedit `ui-context.md` langsung — perubahan token adalah
  keputusan engineer, lewat `/selcy-sync`.
- Never mendesain dua fitur dalam satu run.
- Never menulis kode aplikasi — itu `/selcy-implement`'s.

## Portability

Any Agent Skills client on macOS, Linux, Windows. `pen` CLI is the only
required tool. Shell snippets are POSIX reference, not literal scripts.
