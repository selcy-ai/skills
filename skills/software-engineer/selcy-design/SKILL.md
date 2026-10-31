---
name: selcy-design
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion
description: "Run /selcy-design before /selcy-implement for any feature whose spec carries a ## Design Reference. Works on two backends — pen.dev CLI (Linux) or Open Design (VS Code / Windows / opencode) — recorded once in ui-context.md. Either way it appends the feature's screens to the project's single design collection, resolves cross-screen inconsistencies before they reach the builder, exports the builder's -ref.html plus PNG, and writes design/NN-name.md naming screens and tokens. Pair worker with /selcy-implement for UI."
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
3. The project's single design collection. Backend A: the `.pen` file
   (path named in `ui-context.md`, default `design/<project>.pen`) —
   appended to, never replaced. Backend B: the Open Design `collectionId`
   (recorded in `ui-context.md` and `design/00-kickoff.md`).
4. Prior `design/NN-*.md` notes — for consistency with screens already
   designed, not for re-reading the whole history.

## The two backends

Skill ini punya dua backend. Pilihannya diambil **sekali per proyek, saat
wawancara `/selcy-sdd`**, dan direkam di `context/ui-context.md` sebagai
baris `design backend: pen` atau `design backend: open-design`. Bukan
per-run, dan bukan keputusan orchestrator — orchestrator hanya melihat
`## Design Reference` dan mendelegasikan. Kalau baris itu tidak ada saat
run pertama, tanyakan ke engineer dan tulis dulu ke `ui-context.md`.

| | Backend A — pen.dev | Backend B — Open Design |
|---|---|---|
| Host | Linux, `pen` CLI terpasang | Windows / VS Code / opencode, MCP Open Design |
| Bentuk karya | satu `.pen`, semua screen jadi frame di dalamnya | satu HTML per screen, semuanya dalam satu `collectionId` |
| Untuk builder | `design/<project>-ref.html` | `design/NN-<slug>-ref.html` + index `design/<project>-ref.html` |
| Untuk manusia | PNG per frame | PNG per screen |
| Pengganti `.pen` utuh | `.pen` itu sendiri | index `design/<project>-ref.html` |
| PDF | — | **tertunda.** Open Design export PDF per artifact, tidak menggabungkan semua screen jadi satu PDF; sekarang pakai PNG per screen dulu |

**Nama artifak yang diterima downstream (`/selcy-implement`,
`/selcy-check`) sama di kedua backend**: `design/NN-*.md` selalu ada,
`-ref.html` selalu ada, PNG selalu ada. Jangan pernah mengubah penamaan
itu — tujuh file lain menganggap kontrak ini tetap.

## Backend A's shape: the single .pen rule

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

## Backend A — the pen.dev CLI

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

## Backend A — Export — the handoff artifacts

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

## Backend B — Open Design (Windows, VS Code, opencode)

Backend untuk host tanpa `pen` CLI. Semua interaksi lewat tool Open
Design (MCP — sudah terpasang di VS Code dan opencode). Lihat tabel di
atas untuk pemetaan artifaknya; aturan di bawah adalah urutan kerjanya.

### Design system bridge (sekali per proyek)

`ui-context.md` adalah sumber kebenaran. Sekali, saat design kickoff:
pindahkan tokennya (warna, font, radius) menjadi design system Open Design
lewat `create_open_design_design_system` (name = nama proyek), lalu
`set_active_design_system`. Setiap screen memakai design system ini —
jangan biarkan Open Design memakai token acak. Kalau `ui-context.md`
berubah (lewat `/selcy-sync`), perbarui design system-nya juga. Satu
arah: `ui-context.md` → design system, tidak pernah sebaliknya.

### Tiap screen = satu artifact, semuanya dalam satu collection

Aturan "satu produk = satu file" di backend B berarti: **satu
`collectionId` per proyek** (slug, misalnya `bmkg-screens`), dipakai
verbatim di setiap `prepare_open_design_brief` dan
`register_open_design_artifact`. Artifact lepas tanpa collection = `.pen`
per halaman, dilarang.

Per screen:

1. `prepare_open_design_brief` dengan `skillId` dari surface yang pas —
   daftarnya lewat `list_open_design_skills` dengan `surface: "prototype"`
   (mis. `od:prototype:web-prototype` untuk halaman desktop umum,
   `od:prototype:saas-landing` untuk landing). `brief` berisi screen dari
   `## Design Reference` + token; sertakan `collectionId`,
   `collectionName`, `screenRole` (mis. `dashboard`), dan `screenTotal`.
   Jangan pilih entry `stub: true`.
2. Tulis HTML-nya sesuai instructions yang dikembalikan.
3. `register_open_design_artifact` dengan `collectionId`/`collectionName`,
   `screenIndex` (0-based), `screenRole`, kind `prototype`.
4. `check_open_design_artifact` — render + preflight (overflow, kontras,
   teks hilang, safe area). Fix setiap **error**, lihat screenshotnya
   (balance, hierarki, area terlalu penuh/kosong), maksimal dua ronde
   fix, lapor sisanya. Ini pengganti langkah "buka render PNG per frame"
   backend A.
5. Ulangi per screen. Mobile 390px (dan tablet 820px bila spec minta)
   adalah **artifact terpisah** dalam collection yang sama, `screenRole`-nya
   `<nama>-mobile`.

Artifact dispesifikasikan dengan `screenTotal` agar `screenIndex` akurat;
screen mobile ikut nomornya sendiri.

### Backend B — Export — tiga artifak

Setelah semua screen bersih dari `check`:

- **PNG per screen** — `export_open_design_artifact` format `png`, scale 2,
  satu per screen, disimpan ke `design/NN-<slug>.png`. Inilah yang
  dikirim ke engineer.
- **HTML builder** — format `standalone` per screen →
  `design/NN-<slug>-ref.html`. HTML self-contained yang render-nya persis
  seperti prototipe. Ini kontrak visual builder — struktur dan token,
  bukan kode untuk dicopy.
- **Index** — `design/<project>-ref.html`: satu halaman sederhana yang
  me-link setiap `-ref.html` + PNG dari **semua** screen yang sudah jadi
  (semua fitur, bukan cuma run ini). Ditulis ulang setiap run agar tetap
  jadi peta isi — peran yang sama dengan frame `00 · Panduan` backend A.

Backend B saat ini **tidak export PDF** (lihat tabel). Kalau engineer
meminta satu PDF berisi semua halaman, catat sebagai permintaan tertunda
di `design/NN-*.md` — bukan alasan memblokir run.

## Output: `design/NN-<nama>.md`

Backend-neutral. Isi minimum setiap run:

- **Frame index**: frame id + nama + breakpoint yang dibuat run ini
  (backend B: `screenIndex` + `collectionId` + `screenRole`)
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
- Backend belum tercatat di `ui-context.md`? → tanyakan engineer, tulis
  dulu baris `design backend:`-nya. Lanjut dengan backend yang tercatat.
- Karya produk belum ada (backend A: `.pen`; backend B: `collectionId`
  terdaftar) → ini run pertama: jalankan **design kickoff** (lihat bawah),
  bukan desain fitur.
- Karya sudah ada → desain fitur (Step 2).

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

**Backend B:** ganti langkah 1–2 dengan **design system bridge**
(`create_open_design_design_system` + `set_active_design_system` dari
`ui-context.md`, lihat bagian Backend B), dan catat `collectionId` proyek
di `design/00-kickoff.md`. Tidak ada frame `00 · Panduan` — peran index
dipegang `design/<project>-ref.html`. Langkah 3 (PNG + persetujuan)
tetap: ekspor PNG screen kickoff (shell navigasi saja) sebelum fitur
pertama dibangun.

### Step 2: Design the feature

1. Baca spec + `ui-context.md` + frame yang sudah ada di `.pen` (konsistensi).
2. Terapkan quality bar (`antislop*`, `ui-ux-pro-max`, cek referensi
   komponen).
3. Generate dengan prompt multi-frame, iterate dengan `--in/--out` sampai
   frames ini benar. (Backend B: tiap screen adalah artifact baru dalam
   collection yang sama; konsistensi dijaga oleh design system +
   `screenRole`, bukan `--in/--out`.)
4. **Verifikasi inkonsistensi**: buka render PNG per frame, bandingkan
   field/komponen yang sama antar breakpoint. Resolve sebelum export.
   (Backend B: ini dijalankan `check_open_design_artifact` per artifact,
   termasuk screenshot dan preflight.)
5. Export PNG per frame + `-ref.html` (html-tailwind/html-css sesuai stack).
   (Backend B: tiga artifak di bagian Backend B — PNG per screen, `-ref.html`
   per screen, index.)
6. Update frame `00 · Panduan` (backend A) atau index
   `design/<project>-ref.html` (backend B) agar tetap menjadi indeks yang
   akurat.

### Step 3: Write the note

Tulis `design/NN-<nama>.md` (lihat format di atas). Update
`progress-tracker.md` satu baris: feature NN designed, artifacts at
`design/NN-*.md` + `-ref.html`.

### Step 4: Handoff

Kirim PNG + `.pen` + `-ref.html` ke engineer (MEDIA: paths, satu per baris).
Backend B: PNG per screen + `NN-<slug>-ref.html` + index
`<project>-ref.html`; **tidak ada `.pen`** dan **tidak ada PDF** — kirim PNG
saja. Pengiriman tidak pernah otomatis: skill wajib menulis pesan ini,
satu path per baris, di akhir setiap run. Tanpa pesan ini, engineer tidak
menerima apa-apa.
Lapor: frame apa yang dibuat, keputusan inkonsistensi apa yang diambil,
komponen siap pakai apa yang dipakai, dan tidak ada langkah verifikasi yang
dilewati. Next step selalu: `/selcy-implement NN` di chat baru.

## What this skill never does

- Never membuat file `.pen` per halaman — satu produk, satu file. (Backend
  B: satu `collectionId`, tidak pernah artifact lepas.)
- Never membiarkan Open Design memakai token acak — selalu lewat design
  system yang dibangun dari `ui-context.md`.
- Never melanjutkan saat frame kontradiktif — resolve di sini, bukan di build.
- Never mengABAIKAN quality bar (antislop, aksesibilitas, touch target).
- Never mengedit `ui-context.md` langsung — perubahan token adalah
  keputusan engineer, lewat `/selcy-sync`.
- Never mendesain dua fitur dalam satu run.
- Never menulis kode aplikasi — itu `/selcy-implement`'s.
- Never mengubah nama artifak (`design/NN-*.md`, `-ref.html`, PNG) —
  tujuh skill lain bergantung pada kontrak itu di kedua backend.

## Portability

Any Agent Skills client on macOS, Linux, Windows. Backend A needs the
`pen` CLI (Linux); backend B needs the Open Design MCP (VS Code, opencode,
atau agent lain yang mendukung MCP). Salah satu harus ada; backend mana
yang dipakai dicatat di `ui-context.md`. Shell snippets are POSIX
reference, not literal scripts.
