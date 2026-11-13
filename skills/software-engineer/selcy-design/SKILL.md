---
name: selcy-design
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion
description: "Run /selcy-design before /selcy-implement for any feature whose spec carries a ## Design Reference. Works on three backends — pen.dev CLI (Linux), Open Design via MCP (Linux daemon or Windows / VS Code / opencode) — recorded once in ui-context.md. Auto-detects OS and tool availability, proposes a default, asks the engineer once per project. Either way it appends the feature's screens to the project's single design collection, resolves cross-screen inconsistencies before they reach the builder, exports the builder's -ref.html plus PNG, and writes design/NN-name.md naming screens and tokens. /selcy-design full is the batch mode: every UI feature in one chat, one review of the whole surface, for products whose data model is already stable. Pair worker with /selcy-implement for UI."
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

## The three backends, and how to pick one

Skill ini punya tiga backend. Pilihannya **bukan manual murni, dan bukan
otomatis murni — deteksi dulu, lalu engineer konfirmasi sekali per proyek**:

1. **Deteksi lingkungan saat run** (bukan saat wawancara `/selcy-sdd`):
   - OS: `uname -s` → `Linux` / `Windows` (di Windows, ingat Git Bash
     `uname -s` melaporkan `MINGW*`/`MSYS*` — itu tetap Windows).
   - `pen` CLI: `command -v pen`.
   - Open Design MCP: apakah tool `mcp__open_design__list_projects` (atau
     `list_skills`) tersedia di sesi ini. Di daemon Linux, path data ada di
     `/root/open-design/.od/` (home user: `~/open-design/.od/`).
2. **Usulkan default** dari tabel di bawah. Satu backend saja.
3. **Tanyakan engineer di run pertama** (satu pertanyaan, satu jawaban,
   opsi default ditandai `(recommended)`), lalu **tulis baris
   `design backend: <nilai>` ke `context/ui-context.md`**. Setelah itu
   backend tercatat — run berikutnya membaca baris itu dan tidak bertanya
   lagi. Bukan per-run, dan bukan keputusan orchestrator — orchestrator
   hanya melihat `## Design Reference` dan mendelegasikan.
4. Kalau baris `design backend:` **sudah ada**, gunakan itu verbatim.
   Engineer tetap berhak override kapan saja; perubahan ditulis lewat
   `/selcy-sync`, bukan diam-diam di sini.

**Tabel deteksi** (baris pertama yang cocok menang, dari atas ke bawah):

| OS | `pen` CLI | Open Design MCP | Backend yang diusulkan |
|---|---|---|---|
| Linux | ada | ada | **C — open-design** (default di server ini; pen.dev fallback) |
| Linux | ada | tidak ada | **A — pen** |
| Linux | tidak ada | ada | **C — open-design** |
| Linux | tidak ada | tidak ada | stop: tidak ada backend. Minta engineer pasang salah satu. |
| Windows | — | ada (VS Code/opencode MCP) | **B — open-design (Windows flow)** |
| Windows | — | tidak ada | stop: pasang Open Design MCP; `pen` CLI tidak mendukung Windows. |
| macOS | ada | tidak ada | **A — pen** (sama seperti Linux) |
| macOS | — | — | stop: belum ada backend teruji. Minta engineer memilih. |

Lalu nilai backend-nya: `pen`, `open-design`, atau `open-design-windows`.
Nilai `open-design` di Linux/Windows memilih backend C atau B sesuai OS —
lihat kontrak masing-masing di bawah.

| | Backend A — pen.dev | Backend B — Open Design (Windows) | Backend C — Open Design (Linux daemon) |
|---|---|---|---|
| Host | Linux, `pen` CLI terpasang | Windows / VS Code / opencode, MCP Open Design | Linux, daemon Open Design aktif + MCP terkoneksi |
| Cara kerja | kamu menulis prompt multi-frame; pen.dev men-generate frame | Hermes menulis HTML → register → check | Open Design punya **agen sendiri** (agentId `hermes`); kamu `start_run` lalu poll `get_run` |
| Bentuk karya | satu `.pen`, semua screen jadi frame di dalamnya | satu HTML per screen, semuanya dalam satu `collectionId` | satu project OD per proyek SELCy; satu screen = satu artifact dalam project itu |
| Untuk builder | `design/<project>-ref.html` | `.open-design/NN-<slug>/exports/NN-<slug>.html` + symlink `design/NN-<slug>-ref.html` + index `design/<project>-ref.html` | symlink `design/NN-<slug>-ref.html` → artifact OD (lihat Backend C) |
| Untuk manusia | PNG per frame | PNG per screen, `.open-design/NN-<slug>/exports/` + symlink di `design/` | previewUrl OD + PNG bila di-export; utamanya HTML + previewUrl |
| Pengganti `.pen` utuh | `.pen` itu sendiri | index `design/<project>-ref.html` | satu project OD berisi semua screen — itulah "file tunggal"-nya |
| PDF | — | **tertunda** (lihat Backend B) | **tidak ada export PDF**; render PNG via previewUrl/browser |

**Nama artifak yang diterima downstream (`/selcy-implement`,
`/selcy-check`) sama di ketiga backend**: `design/NN-*.md` selalu ada,
`-ref.html` selalu ada, PNG/preview selalu ada. Jangan pernah mengubah
penamaan itu — tujuh file lain menganggap kontrak ini tetap.

**Aturan yang dibagi Backend B dan C.** Tools-nya berbeda (B = MCP VS
Code/opencode, C = daemon Linux), tapi kedua backend ini tunduk pada aturan
yang sama, ditulis sekali di sini:

- **`ui-context.md` adalah sumber kebenaran, satu arah.** Token mengalir
  `ui-context.md` → design system Open Design, tidak pernah sebaliknya.
  Kalau `ui-context.md` berubah (lewat `/selcy-sync`), design system-nya
  dibaca ulang: di B perbarui lewat `set_active_design_system`, di C
  pertimbangkan ulang slug katalognya.
- **`stub: true` dilarang** — di `list_open_design_skills` (B) maupun
  `list_skills` (C), jangan pilih entry yang `stub: true`.

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

## Backend C — Open Design di Linux (daemon + MCP)

Backend untuk host Linux tempat daemon Open Design berjalan dan MCP-nya
terkoneksi dari sesi Hermes/opencode ini. Semua interaksi lewat tool MCP
`mcp__open_design__*`.

**Penting: agen OD yang men-generate, bukan kamu.** Backend A menulis
prompt lalu `pen` men-generate frame; backend B kamu sendiri menulis
HTML-nya. Backend C **berbeda**: Open Design memilik agen internal
(`agentId: "hermes"`) yang menulis kode HTML. Tugasmu adalah menulis prompt
yang presisi lalu poll sampai selesai — **jangan tulis HTML sendiri
menggantikan agen OD**, karena kualitas desain datang dari pipelinenya.
Kalaupun hasilnya kurang, iterate lewat prompt baru, bukan dengan
menimpa file manual.

**Kamu adalah operator MCP, bukan desainer HTML.** Lihat Step C4 untuk
alur lengkapnya, dan "Backend C vs A/B" di akhir bagian ini untuk
hal-hal yang belum pernah ada di backend A/B.

### Step C0: Pastikan koneksi dan akun

- `mcp__open_design__list_projects` — harus merespons. Kalau gagal,
  fallback ke backend A (pen.dev), atau stop bila keduanya tidak ada.
- `get_vela_login_status` — `loggedIn: true` wajib (login daemon, bukan
  biaya). **Catat `account.plan` dan `account.balanceUsd`** — ada untuk
  kelengkapan, **tapi umumnya tidak relevan untuk backend C di host
  self-hosted**: daemon memakai `agentId` dan model dari
  `app-config.json` (`agentModels.<agentId>.model`), dan biaya mengalir
  lewat endpoint yang sudah kamu konfigurasi sendiri (lihat di bawah).
  Sampaikan kalau nilainya mencurigakan (mis. plan cloud aktif padahal
  yang dipakai model local), bukan sebagai peringatan biaya default.
- **Cek dari mana biaya benar-benar mengalir** sebelum run pertama:
  1. `mcp__open_design__list_agents` — daftar agent terpasang + model
     default-nya. Yang dipakai adalah `agentId` dari `app-config.json`.
  2. Konfigurasi model: `agentModels.<agentId>.model` di
     `<OD data dir>/app-config.json`. Nilai custom (mis.
     `custom:omniroute:...`) berarti endpoint **milikmu sendiri** —
     open source atau provider local, gratis menurut aturan endpoint
     itu, sama seperti Hermes. Kalau nilainya model Cloud berbayar
     (mis. claude-opus), **barulah** ada biaya OD per run.
  3. Event log run: `grep 'API call #' <eventsLogPath>` menampilkan
     `model=… provider=… cache=…` per call. `provider=custom` +
     `cache=100%` = arus ke endpointmu, pada dasarnya $0.
- **Kesalahpahaman umum** (diharapkan ditiadakan): `plan: free` /
  `balance: $0` di `get_vela_login_status` **bukan** sinyal "OD akan
  gagal di run besar". Akun daemon login itu untuk autentikasi daemon,
  bukan billing inferensi. Inferensi mengikuti model yang dikonfigurasi
  daemon — persis seperti Hermes. OD self-hosted memang **bisa** pakai
  model open-source atau langsung dari endpoint Hermes (agentId
  `hermes`), tidak seperti pen.dev yang model-nya diatur vendor.
- Catat outputnya di `design/00-kickoff.md`.

### Step C1: Buat project (sekali per proyek SELCy)

**Satu proyek SELCy = satu project OD.** Ini pengganti "satu `.pen`
utuh" — jangan pernah membuat project OD per screen.

```text
create_project(name: "<project-slug>" [, skill: "<skillId>"])
  → projectId  (contoh: "bmkg-dashboard-a1b2c3")
```

- `name` = slug proyek, stabil, dari `project-overview.md`.
- **Catat `projectId` di `ui-context.md` (baris `open-design project
  id:`) dan di `design/00-kickoff.md`.** Ini wajib: semua run
  berikutnya membaca projectId itu, dan ID di-generate daemon (tidak
  bisa ditebak).
- `skill` opsional di sini; bisa juga dikirim per-run di `start_run`.

### Step C2: Pilih skillId untuk screen ini

Daftar lengkap lewat `list_skills`. Penamaan **bukan**
`od:prototype:...` — id skill bermacam-macam. Pilihan
umum (verifikasi id di host-mu karena bisa berubah):

| Kebutuhan screen | skillId kandidat |
|---|---|
| Dashboard, app screen, UI aplikasi umum | `frontend-design`, `web-artifacts-builder`, `artifacts-builder` |
| Landing page / halaman publik | `frontend-design`, `frontend-dev` |
| Editorial / minimalis | `minimalist-ui` |
| Login/auth flow (mobile) | `login-flow` |
| Data-viz berat | `d3-visualization`, `data-report` |
| Clone tampilan eksisting | `web-clone` |

Setiap skill punya `designSystemRequired` — kalau `true`, run butuh
design system terpasang (Step C3) atau akan gagal/tidak sesuai token.

### Step C3: Design system bridge (sekali per proyek)

`ui-context.md` tetap sumber kebenaran, tapi backend C **tidak membuat
design system custom** — Open Design menyediakan katalog siap pakai:

1. `list_resources` → daftar `od://design-systems/<slug>/DESIGN.md`
   (ratusan pilihan: `shadcn`, `vercel`, `linear-app`, `stripe`,
   `supabase`, `minimal`, `neobrutalism`, `dashboard`, …).
2. Baca kandidatnya dengan `read_resource("od://design-systems/<slug>/DESIGN.md")`
   — format: warna hex, typography scale, spacing, motion, anti-pattern.
3. Pilih slug yang paling dekat dgn `ui-context.md`. Kalau tidak ada
   yang cocok, pilih `default` dan perjelas prompt di `start_run` dengan
   token eksplisit (warna, font, radius) dari `ui-context.md`.
4. Pasang saat `create_project(designSystem: "od://design-systems/<slug>")`
   atau simpan untuk dikirim per-run.

Aturan: **pemilihan slug adalah keputusan engineer** — kandidat
(dengan ringkasan warna/font) wajib disampaikan di kickoff, bukan
dipilih diam-diam. Aturan satu arah dan follow-up `selcy-sync` ada di
blok "Aturan yang dibagi B dan C" di atas.

### Step C4: Tiap screen = satu run

Loop per screen dari `## Design Reference`:

1. `start_run(project: "<projectId>", skill: "<skillId>", prompt: “…”)`.
   **`prompt` wajib memuat**: screen apa, lebar (1360/390/820), isi
   per blok, token warna/font/radius dari `ui-context.md` atau rujukan
   ke design system slug, dan `screenRole`. Sertakan eksplisit:
   “screen ini milik fitur NN proyek <produk>—pertahankan konsistensi
   dgn screen lain dalam project OD ini.”
2. `start_run` langsung mengembalikan `runId` — **jangan memblokir turn kamu sambil menunggu di dalamnya**. Hint resmi: run butuh 5–30 menit.
3. Poll `get_run(runId)` setiap 30–60 detik. `status: "running"` +
   mtime file statis = agen sedang berpikir, **bukan hang** — jangan
   `cancel_run` karena tidak sabar, dan **jangan substitusi
   `write_file`/`create_artifact` untuk menulis desain sendiri**.
   Laporkan “still working” ke engineer sambil menunggu.
4. Terminal: `status: "succeeded"` + `artifactPaths` + `deliverableValid`
   + `previewUrl`. `agentMessage` berisi ringkasan agen OD — baca dan
   sampaikan ke engineer. Kalau `failed`, lihat `failureCategory` /
   `failureAction`; coba ulang dgn prompt yang diperbaiki (paling banyak
   2 ronde), lalu laporkan jika masih gagal.
   **Kasus khusus `route: "full_plan"`**: OD menjalankan rencana
   2-run. Run pertama sukses tapi `artifactCount: 0` dan
   `deliverableValidation: "no_artifact"` — itu **bukan kegagalan**.
   `strategyTask` memuat `nextRunId`, dan `display.runIds` menambah satu
   run lagi (`inputStage: "production"`). Lanjutkan poll ke runId baru
   itu sampai benar-benar terminal. Jangan mengira run pertama gagal
   dan memulai `start_run` baru — akan menggandakan pekerjaan dan
   merusak rantai percakapan.
5. Mobile 390px adalah **run terpisah** dalam project yang sama, dengan
   prompt eksplisit "versi mobile, 390px, dari screen <nama>".

Satu hal yang tidak ada di backend A/B: **OD menulis artifact ke path
generate-nya sendiri** (`artifactPaths`) di dalam project OD, **bukan ke
`design/` proyek SELCy**. Kontrak `design/` dijaga lewat symlink —
lihat Step C5.

### Step C5: Symlink ke `design/` (wajib setiap run)

`/selcy-implement` dan `/selcy-check` membaca `design/` — kontrak yang
tidak boleh berubah. Setelah run sukses:

```bash
# 1. Resolve lokasi fisik artifact. JANGAN asumsi path tetap — dapatkan
#    dari MCP, lalu konversi ke relatif dengan python/os.path. Menghitung
#    ../../ manual adalah sumber bug paling umum di langkah ini.
python3 - "$PROJECT_DIR" "$ARTIFACT_PATH" "$OD_DATA_DIR" <<'PY'
import os, sys
project_dir, artifact, od_data_dir = sys.argv[1], sys.argv[2], sys.argv[3]
target = os.path.join(od_data_dir, artifact)
link   = os.path.join(project_dir, 'design', 'NN-<slug>-ref.html')
os.makedirs(os.path.dirname(link), exist_ok=True)
if os.path.islink(link) or os.path.exists(link):
    os.remove(link)
os.symlink(os.path.relpath(target, os.path.dirname(link)), link)
print(link, '->', os.readlink(link))
PY
```

**Cara menemukan `OD_DATA_DIR`** (urutan, berhenti di yang pertama
berhasil):

1. `get_project(project: "<projectId>")` → **`resolvedDir`** (paling
   andal; jalankan ini dulu setiap run).
2. Fallback — cari direktori project secara fisik:
   `find /root/open-design/.od "$HOME/open-design/.od" -maxdepth 3 -type d -name "<projectId>"`.
   Path bervariasi per host dan versi daemon; gunakan hanya hasil yang
   persis cocok dengan `projectId` dari `get_run`.

Aturan:

- **Relative, bukan absolute** — link absolute tidak portabel antar mesin
  engineer. `os.path.relpath` yang menghitungnya, **bukan kamu**; contoh
  `../../open-design/.od/projects/…` di skill ini hanya ilustrasi, dan
  jumlah `../` tidak boleh ditulis tangan. Kalau project SELCy dan data
  OD berada di filesystem berbeda (relpath tidak mungkin), lihat
  pengecualian di bawah.
- Path fisik bisa berubah antar versi daemon — **selalu resolve dari
  `get_run.artifactPaths` + `get_project.resolvedDir`**, lalu
  konversi ke relative. Jangan hardcode `probe/…` atau `exports/…`.
- `artifactRef` (`projectId` + `entryFile`) adalah identitas stabil —
  simpan di `design/NN-*.md`. `previewUrl`/`studioUrl` **tidak stabil**
  (berubah saat daemon restart) — simpan sebagai info tambahan saja.
- `design/NN-<slug>.md` selalu file asli, bukan symlink.
- **Absolute path dibolehkan sebagai fallback** kalau project SELCy
  dan data OD beda filesystem (symlink relative tidak bisa menembus filesystem boundary) —
  tetapi wajib dicatat di `design/NN-*.md` sebagai pengecualian.

### Backend C vs A/B — ringkasan anti-bingung

- **Tidak ada `collectionId`.** Padanannya = `projectId`. Jangan
  mencari tool `register_open_design_artifact` / `prepare_open_design_brief`
  / `check_open_design_artifact` / `export_open_design_artifact` /
  `create_open_design_design_system` — tool itu **tidak ada di MCP
  Open Design yang sebenarnya** (nama asli: `create_artifact`,
  `collect_brief`, `start_run`, `get_run`, `get_artifact`).
- **Tidak ada anda menulis HTML.** Agen OD yang menulis. Lihat Step C4.
- **Run adalah satuan kerja**: satu screen per run. Jangan merge banyak
  screen ke satu run agar "cepat" — konsistensi antar-screen
  lain jadi tidak terjaga.
- **Do not open PNG** aturan backend A berlaku di sini: previewUrl OD
  cukup, jangan load multi-megabyte PNG ke vision context (sama
  crashnya).

## Backend B — Open Design (Windows, VS Code, opencode)

Backend untuk host tanpa `pen` CLI. Semua interaksi lewat tool Open
Design (MCP — sudah terpasang di VS Code dan opencode). Lihat tabel di
atas untuk pemetaan artifaknya; aturan di bawah adalah urutan kerjanya.

### Semua artifak hidup di `.open-design/`

Open Design **hanya menampilkan artifact yang berada di dalam output
 directory-nya** (default `.open-design/`, lihat setting
`openDesign.outputDirectory`). Artifact yang diregister di luar folder
itu technically valid — manifest tersimpan, preview terbuka, check dan
export jalan — **tetapi tidak muncul di history / Recents dashboard**,
jadi engineer tidak bisa melihat, mengaudit, atau memberi komentar pada
layar yang sudah dibuat. Ini bukan bug; ini alur yang tidak boleh
dilewati.

Konsekuensinya: setiap screen Backend B ditulis langsung ke
**`.open-design/NN-<slug>/NN-<slug>.html`** (entry file + manifest), dan
export-nya ke `.open-design/NN-<slug>/exports/`. `design/` tetap
menjadi kontrak downstream (dibaca `/selcy-implement` dan
`/selcy-check`), yang dijaga dengan symlink — lihat bagian Export.

### Design system bridge (sekali per proyek)

`ui-context.md` adalah sumber kebenaran. Sekali, saat design kickoff:
pindahkan tokennya (warna, font, radius) menjadi design system Open Design
lewat `create_open_design_design_system` (name = nama proyek), lalu
`set_active_design_system`. Setiap screen memakai design system ini —
jangan biarkan Open Design memakai token acak. Aturan satu arah dan
follow-up `selcy-sync` ditulis sekali di blok "Aturan yang dibagi B dan C"
di atas.

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
2. Tulis HTML-nya sesuai instructions yang dikembalikan, langsung ke
   `.open-design/NN-<slug>/NN-<slug>.html` (bukan `design/` — lihat aturan
   output directory di bawah).
3. `register_open_design_artifact` dengan `collectionId`/`collectionName`,
   `screenIndex` (0-based), `screenRole`, kind `prototype`, entryPath di
   `.open-design/NN-<slug>/NN-<slug>.html`.
4. `check_open_design_artifact` — render + preflight (overflow, kontras,
   teks hilang, safe area). Fix setiap **error**, lihat screenshotnya
   (balance, hierarki, area terlalu penuh/kosong), maksimal dua ronde
   fix, lapor sisanya. **Warning kontras juga wajib diperbaiki**, bukan
   diabaikan — lihat aturan kontras di bagian design system bridge. Ini
   pengganti langkah "buka render PNG per frame" backend A.
5. Ulangi per screen. Mobile 390px (dan tablet 820px bila spec minta)
   adalah **artifact terpisah** dalam collection yang sama, `screenRole`-nya
   `<nama>-mobile`.

Artifact dispesifikasikan dengan `screenTotal` agar `screenIndex` akurat;
screen mobile ikut nomornya sendiri.

### Backend B — Export — tiga artifak

Setelah semua screen bersih dari `check`:

- **PNG per screen** — `export_open_design_artifact` format `png`, scale 2,
  satu per screen, masuk ke `.open-design/NN-<slug>/exports/`. Inilah yang
  dikirim ke engineer.
- **HTML builder** — format `standalone` per screen,
  `.open-design/NN-<slug>/exports/NN-<slug>.html`. **Nama file ikut entry
  file** —Export selalu menulis `<nama-entry>.html`, tidak menambah `-ref`.
  Karena entry file-nya sudah `NN-<slug>.html` (aturan folder di atas),
  hasilnya `NN-<slug>.html` di `exports/`. Jangan harap
  `NN-<slug>-ref.html`; symlink ke `design/` (lihat bawah) yang membawa
  nama `-ref.html` tersebut. HTML self-contained yang render-nya persis
  seperti prototipe. Ini kontrak visual builder — struktur dan token,
  bukan kode untuk dicopy.
- **Index** — `design/<project>-ref.html`, satu halaman sederhana yang
  me-link setiap `-ref.html` + PNG dari **semua** screen yang sudah jadi
  (semua fitur, bukan cuma run ini). Ditulis ulang setiap run agar tetap
  jadi peta isi — peran yang sama dengan frame `00 · Panduan` backend A.

Backend B saat ini **tidak export PDF** (lihat tabel). Kalau engineer
meminta satu PDF berisi semua halaman, catat sebagai permintaan tertunda
di `design/NN-*.md` — bukan alasan memblokir run.

### Symlink: jembatan ke `design/` (wajib setiap export)

`/selcy-implement` dan `/selcy-check` membaca `design/` — itu kontrak
yang tidak boleh berubah. Solusinya **bukan** menduplikasi file (dua
copy PNG jalan terpisah dan bisa drift — copy pertama jadi basi saat
re-export), tapi symlink:

```bash
# Linux / macOS (Git Bash di Windows)
ln -s ../../.open-design/NN-<slug>/exports/NN-<slug>.html design/NN-<slug>-ref.html
ln -s ../../.open-design/NN-<slug>/exports/NN-<slug>.png      design/NN-<slug>.png

# Windows native (butuh hak symlink — cmd mklink, BUKAN PowerShell
# New-Item yang juga butuh Developer Mode)
cmd /c mklink "design\NN-<slug>-ref.html" "..\.open-design\NN-<slug>\exports\NN-<slug>.html"
cmd /c mklink "design\NN-<slug>.png"      "..\.open-design\NN-<slug>\exports\NN-<slug>.png"
```

Aturan:

- **Dibuat sekali, per artifact, tepat setelah export** — jangan
  ditunda ke akhir run. Kalau symlink sudah ada dari run sebelumnya,
  lewati (re-export overwrites the target file, link tetap).
- **Absolute path tidak boleh** — symlink absolute tidak portabel antar
  mesin engineer. Selalu relative dari `design/`. (Catatan: bahkan link
  absolute tetap bisa dibaca reader, tapi anggap sebagai bug.)
- **PowerShell `New-Item -ItemType SymbolicLink` gagal tanpa Developer
  Mode**, bahkan kalau `cmd /c mklink` di mesin yang sama berhasil. Kalau
  `mklink` juga gagal (akun tanpa hak symlink), masuk fallback.
- **Fallback kalau symlink ditolak** (host tanpa Developer Mode/hak
  admin di Windows): tulis `design/NN-<slug>-ref.html` sebagai file
  asli (copy), dan catat di `design/NN-*.md` bahwa artifak itu bukan
  link — supaya engineer tanda tangan drift-nya, dan `progress-tracker.md`
  perlu diupdate saat re-export.
- `design/NN-<slug>.md` selalu file asli, bukan symlink.

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
- **Lokasi artifak backend B**: `.open-design/NN-<slug>/exports/NN-<slug>.png`
  + `.../NN-<slug>.html` + symlink `design/NN-<slug>-ref.html` + index
  `design/<project>-ref.html`.
- **Lokasi artifak backend C**: `projectId` + `artifactPaths` +
  `previewUrl` (dari `get_run`), `artifactRef` (projectId + entryFile),
  symlink `design/NN-<slug>-ref.html` → file di project OD.

File ini adalah apa yang `/selcy-implement` baca sebagai kontrak visual,
bersama `-ref.html`.

## Commands

Satu perintah, mode diambil dari argumen:

- **No argument** → mode per-fitur (default). Desain satu fitur, satu
  obrolan, lalu `/selcy-implement NN` di obrolan baru.
- **`full`** → mode batch. Desain setiap fitur UI dalam satu obrolan,
  berurutan, lalu satu tinjauan gabungan dari seluruh surface. Mode ini
  menggantikan `/selcy-design-allin` (lihat **Mode full** di bawah).

## Mode full

`/selcy-design full` — pintu batch untuk produk yang data model-nya
sudah stabil. Jalankan **sekali per proyek**, setelah `/selcy-sdd` (atau
`/selcy-audit`) menulis bundle dan **sebelum `/selcy-implement`
pertama**. Menggantikan panggung desain dari loop, bukan menambahinya —
menjalankan mode ini lalu juga menjalankan mode per-fitur adalah
menggandakan kerja.

**Pertukarannya, dinyatakan di depan.** Setiap layar didesain sebelum
umpan balik build ada. Mode per-fitur mendesain fitur 05 **setelah**
fitur 03 dibangun, jadi mockup untuk 05 merefleksikan data model yang
sebenarnya dihasilkan 03. Mode full mendesain 03 dan 05 di waktu yang
sama, jadi mockup 05 merefleksikan apa yang **dikatakan** spec tentang
03. Kalau keduanya berbeda, beberapa layar menjadi usang dan digambar
ulang.

Itu harganya. Apa yang dibeli: satu tinjauan yang mencakup seluruh
permukaan produk, token konsisten di setiap layar secara konstruksi, dan
tidak ada pergantian konteks desain-vs-build per fitur. Engineer
menyetujui satu hal, bukan tujuh.

**Panel pertukaran adalah pertanyaan pertama, wajib, bukan opsional.**
Jangan mulai mendesain dengan asumsi diam-diam — sebuah run yang
mendesain 8 layar yang engineer ingin didesain per-fitur adalah run yang
harus dibuang.

### Step F0: Gate

1. `context/feature-specs/` ada dan berisi specs? Tidak → stop, bundle
   belum siap. Sebut `/selcy-sdd`.
2. `context/ui-context.md` mencatat baris `design backend:`? Tidak →
   stop. Sebut `/selcy-design` (yang punya deteksi) dan katakan engineer
   juga bisa menjawab pertanyaan backend di sana lalu kembali.
   Ya → pakai backend itu verbatim untuk setiap layar.
3. Pindai setiap spec untuk `## Design Reference`. **Tidak ada spec yang
   membawanya** → stop dan katakan: produk ini tidak butuh mockup, mode
   ini tidak ada kerjaan. Itu bukan kegagalan.
4. Spec yang membawanya: **N**. Daftarkan ke engineer dengan nomor dan
   namanya, nyatakan pertukaran di atas, dan ajukan satu pertanyaan:
   batch semua N sekarang (mode ini), atau desain per fitur di dalam
   loop (`/selcy-design NN`)? Defaultnya per fitur. Hanya setelah
   engineer memilih batch, run berlanjut.

### Step F1: Kickoff

Sama seperti Step 1 mode per-fitur (sekali per proyek): baca
`ui-context.md`, buat karya produk di backend tercatat dengan
shell navigasi, ekspor PNG/previewUrl kickoff, tunggu persetujuan
engineer **sebelum** fitur pertama dibangun. Design system adalah
kontrak; mengubahnya setelah 10 layar ada adalah pekerjaan besar.

### Step F2: Desain setiap fitur, berurutan, dalam obrolan ini

Untuk setiap spec yang membawa `## Design Reference`, **urutan fitur**:

1. Baca `## Design Reference` spec itu + `ui-context.md` + layar yang
   sudah didesain di run ini (konsistensi antar-fitur lebih penting di
   sini daripada di mode per-fitur, karena tidak akan ada umpan balik
   build di antaranya).
2. Terapkan quality bar — `antislop`, `antislop-ui`,
   `antislop-layoutmobile`, `antislop-copywriting`, `ui-ux-pro-max`,
   dan referensi komponen siap pakai. Standar yang sama dengan mode
   per-fitur.
3. Desain layar fitur di backend tercatat, mengikuti **Step 2 mode
   per-fitur** untuk backend itu (A/B/C sesuai `design backend:`).
4. **Stop pada kegagalan pertama.** Error backend, gate mismatch,
   inkonsistensi yang tidak bisa diselesaikan — run berhenti di situ dan
   melaporkan fitur mana yang menghentikannya. Jangan lanjut ke fitur
   berikutnya dengan harapan lebih baik; kegagalan di tengah batch
   adalah kegagalan batch. Engineer menyelesaikannya dan re-run dari
   fitur itu.
5. Ekspor per backend tercatat (PNG + `-ref.html` per layar, atau
   previewUrl + symlink di backend C) dan perbarui index
   (`design/<project>-ref.html` atau frame `00 · Panduan`).

**Layar satu fitur harus selesai sepenuhnya sebelum fitur berikutnya
mulai.** Tidak diinterleave. Batch adalah urutan desain per-fitur yang
lengkap, bukan satu desain dari semua layar sekaligus — isolasi yang
membuat kesalahan di satu fitur tidak menjangkau fitur lain tetap
dipertahankan, hanya batas obrolan antar fitur yang dihilangkan.

### Step F3: Tulis catatannya

Satu `design/NN-<nama>.md` per fitur, format yang sama dengan mode
per-fitur (lihat **Output** di atas). Tambah satu baris per fitur di
`progress-tracker.md`: `feature NN designed, artifacts at
design/NN-*.md + -ref.html`.

### Step F4: Tinjauan tunggal — inti dari mode full

Semua layar selesai, engineer melihatnya **bersama-sama, sekali**:

- Setiap `design/NN-*.md`, digabungkan jadi satu laporan dikelompokkan
  per fitur, dengan keputusan inkonsistensi dan komponen siap pakai
  yang dipakai.
- Index (`design/<project>-ref.html` atau frame `00 · Panduan`), yang
  sekarang mencatat setiap layar produk — ini satu-satunya artifak yang
  menampilkan seluruh permukaan Sekaligus, dan di sini lengkap.
- Setiap PNG atau previewUrl, satu path per baris.
- **Screenshot per artifak** (lihat "Screenshot artifak" di bawah):
  satu `design/NN-<slug>.png` per layar produk, path-nya satu per
  baris, supaya engineer melihat prototype sebagai gambar, bukan cuma
  path HTML. Backend A sering sudah menghasilkannya; backend C harus
  dibuat.
- Pengingat pertukaran: layar-layar ini merefleksikan spec, bukan
  perilaku yang sudah dibangun, dan setiap fitur yang build-nya
  mengubah data model bisa membatalkan layar setelahnya.

Engineer menyetujui, meminta perubahan, atau menolak batch. Perubahan
kembali ke Step F2 untuk fitur yang terkena.

### Step F5: Kembalikan ke loop

Setelah persetujuan, produk didesain persis seperti proyek per-fitur:
langkah berikutnya adalah `/selcy-implement NN` per fitur, urutan
fitur, masing-masing di obrolannya sendiri. Orchestrator (jika dipakai)
mengambil card seperti biasa — ia tidak menjalankan `/selcy-design NN`
untuk fitur yang `design/NN-*.md`-nya sudah ada dan baris trackernya
berkata designed.

## Screenshot artifak

Lengkapilah setiap handoff design (Step 4 per-fitur, Step F4 mode full)
dengan satu PNG per layar produk — `design/NN-<slug>.png`. Deliverable
design adalah visual; path HTML saja tidak memperlihatkan hasilnya ke
engineer. `od export --format image` bawaan Open Design hanya jalan di
desktop runtime, jadi jangan andalkan itu di server headless.

**Backend A (pen.dev):** export PNG bawaan sering sudah ada — periksa
`design/*.png` lebih dulu, gunakan yang ada. Jika tidak ada, jalankan
export pen.dev sekali per frame.

**Backend C (Open Design):** artifaknya adalah HTML di luar repo
(`.od/projects/…` via symlink). Screenshot sendiri:

```
/root/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome \
  --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size=1360,900 --screenshot=design/NN-<slug>.png \
  file://<realpath artifact html>
```

Atau binary chromium headless manapun yang terpasang (`chromium`,
`headless-shell`). Gunakan ukuran jendela dari spec (default 1360×900).
Bisa resolusi tinggi (mis. 2×) untuk screenshot yang akan dibaca
engineer sebagai gambar laporan.

shortcut: 3 artifact per run, batas wajar untuk screenshot manual —
lebih dari itu, tulis loop shell satu kali, jangan per-frame fungsi
baru.

## Execution

### Step 0: Route

- Spec punya `## Design Reference`? Tidak → stop, feature ini tidak butuh
  desain. Ya → lanjut.
- Backend belum tercatat di `ui-context.md`? → **deteksi OS +
  ketersediaan** (lihat "The three backends"), usulkan default, tanyakan
  engineer, lalu tulis baris `design backend:`-nya. Lanjut dengan
  backend yang tercatat.
- Karya produk belum ada (backend A: `.pen`; backend B: `collectionId`
  terdaftar; backend C: `projectId` terdaftar di `ui-context.md`) → ini
  run pertama: jalankan **design kickoff** (lihat bawah), bukan desain
  fitur.
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

**Backend C:** ganti langkah 1–2 dengan **Step C0–C3**: cek koneksi MCP
+ akun (sampaikan plan/balance ke engineer), `create_project` (catat
`projectId` ke `ui-context.md` dan `design/00-kickoff.md`), pilih
`skillId` dan design system slug bersama engineer. Kickoff run-nya satu
`start_run` untuk **shell navigasi saja** (header/sidebar/bottom-nav),
kirim `previewUrl` + `agentMessage` ke engineer untuk persetujuan
sebelum fitur pertama dibangun. Tidak ada frame `00 · Panduan` dan tidak
ada PNG wajib — persetujuan lewat previewUrl.

### Step 2: Design the feature

1. Baca spec + `ui-context.md` + frame yang sudah ada di `.pen` (konsistensi).
2. Terapkan quality bar (`antislop*`, `ui-ux-pro-max`, cek referensi
   komponen).
3. Generate dengan prompt multi-frame, iterate dengan `--in/--out` sampai
   frames ini benar. (Backend B: tiap screen adalah artifact baru dalam
   collection yang sama; konsistensi dijaga oleh design system +
   `screenRole`, bukan `--in/--out`. Backend C: tiap screen adalah
   `start_run` terpisah dalam project OD yang sama; konsistensi dijaga
   oleh design system slug + prompt yang menyebut screen lain, lihat
   Step C4.)
4. **Verifikasi inkonsistensi**: buka render PNG per frame, bandingkan
   field/komponen yang sama antar breakpoint. Resolve sebelum export.
   (Backend B: ini dijalankan `check_open_design_artifact` per artifact,
   termasuk screenshot dan preflight. Backend C: baca `agentMessage` +
   `previewUrl` dari `get_run` untuk mengecek hasil tiap run; kalau
   perlu, iterate dengan prompt baru — jangan edit HTML-nya sendiri.)
5. Export PNG per frame + `-ref.html` (html-tailwind/html-css sesuai stack).
   (Backend B: tiga artifak di bagian Backend B — PNG per screen, `-ref.html`
   per screen, index. Semua di `.open-design/NN-<slug>/exports/` kecuali
   index, lalu symlink ke `design/`. Backend C: artifact sudah ditulis
   agen OD ke `artifactPaths`; tugasmu hanya symlink ke `design/` —
   lihat Step C5.)
6. Update frame `00 · Panduan` (backend A) atau index
   `design/<project>-ref.html` (backend B/C) agar tetap menjadi indeks yang
   akurat.

### Step 3: Write the note

Tulis `design/NN-<nama>.md` (lihat format di atas). Update
`progress-tracker.md` satu baris: feature NN designed, artifacts at
`design/NN-*.md` + `-ref.html`.

### Step 4: Handoff

Kirim PNG + `.pen` + `-ref.html` ke engineer (MEDIA: paths, satu per baris).
Backend B: PNG per screen + `NN-<slug>-ref.html` + index
`<project>-ref.html`; **tidak ada `.pen`** dan **tidak ada PDF** — kirim PNG
saja. Sebut path Asli di `.open-design/NN-<slug>/exports/` **dan** linknya
di `design/` (keduanya valid; engineer bisa pakai salah satu).
Backend C: kirim `previewUrl` (URL **lokal daemon**, berlaku untuk sesi
daemon ini saja — ingatkan engineer untuk membuka via `get_run` lagi
kalau sudah restart) + symlink `design/NN-<slug>-ref.html` +
`agentMessage`. **Tidak ada `.pen`, tidak ada PNG wajib** — kirim
previewUrl + symlink saja. Sebut `projectId` dan `artifactRef` juga,
supaya engineer bisa membuka ulang artifact-nya. Lalu screenshot artifak
HTML-nya (lihat "Screenshot artifak") dan kirim PNG-nya juga — previewUrl
daemon tidak permanen, PNG-nya yang bisa engineer lihat kembali. Pengiriman tidak pernah otomatis: skill wajib menulis pesan ini,
satu path per baris, di akhir setiap run. Tanpa pesan ini, engineer tidak
menerima apa-apa.
Lapor: frame apa yang dibuat, keputusan inkonsistensi apa yang diambil,
komponen siap pakai apa yang dipakai, dan tidak ada langkah verifikasi yang
dilewati. Next step selalu: `/selcy-implement NN` di chat baru.

## What this skill never does

- Never membuat file `.pen` per halaman — satu produk, satu file. (Backend
  B: satu `collectionId`, tidak pernah artifact lepas. Backend C: satu
  `projectId`, tidak pernah project OD lepas per screen.)
- Never membiarkan Open Design memakai token acak — selalu lewat design
  system yang dibangun dari `ui-context.md` (backend B) atau design
  system slug OD yang dipilih bersama engineer (backend C).
- Never menulis artifact Backend B di luar `.open-design/` — artifact di
  luar folder itu tidak terlihat di dashboard / Recents, jadi engineer
  tidak bisa mengaudit atau berkomentar. `design/` hanya diisi via symlink
  (atau copy fallback yang dicatat), tidak pernah artifact asli. Backend
  C: artifact ditulis agen OD ke project OD-nya — kamu tidak pernah
  menulis artifact ke `design/` selain via symlink.
- Never menulis HTML sendiri di backend C — itu pekerjaan agen OD
  (agentId `hermes`). Kamu `start_run` + poll + baca hasil. Menimpa
  hasil dengan `write_file`/`create_artifact` adalah pelanggaran kontrak
  pipeline OD dan menghancurkan kualitas desain.
- Never melanjutkan saat frame kontradiktif — resolve di sini, bukan di build.
- Never mengABAIKAN quality bar (antislop, aksesibilitas, touch target).
- Never mengedit `ui-context.md` langsung — perubahan token adalah
  keputusan engineer, lewat `/selcy-sync`.
- Never menulis kode aplikasi — itu `/selcy-implement`'s.
- Never mengubah nama artifak (`design/NN-*.md`, `-ref.html`, PNG) —
  tujuh skill lain bergantung pada kontrak itu di ketiga backend.

## Portability

Any Agent Skills client on macOS, Linux, Windows. Backend A needs the
`pen` CLI (Linux atau macOS). Backend B needs the Open Design MCP (VS
Code, opencode, atau agent lain yang mendukung MCP) di Windows dan
menulis ke output directory Open Design (default `.open-design/`, bisa
diatur lewat `openDesign.outputDirectory`). Backend C needs daemon Open
Design berjalan di host Linux dan MCP terkoneksi dari sesi agen —
artifact ditulis ke `<OD data dir>/projects/<projectId>/` (di host ini
`/root/open-design/.od/`), dan kontrak `design/` dijaga lewat symlink.

Salah satu harus ada; backend mana yang dipakai dicatat di
`ui-context.md` (baris `design backend:`), dipilih lewat deteksi OS +
ketersediaan (lihat "The three backends"). Symlink butuh Developer Mode
atau hak admin di Windows; Git Bash `ln -s` berjalan tanpa keduanya. Di
Linux `ln -sfn` berjalan tanpa hak khusus. Shell snippets are POSIX
reference, not literal scripts.
