# Open Design — jebakan yang sudah dibayar mahal

Backend C (daemon Linux + MCP). Tiap bagian satu masalah + cara
mengenalinya + jalur yang terbukti. Baca saat backend C dipilih; jangan
menghafal, jangan membaca semuanya sebelum run.

## 1. `od export --format image/pdf` — hanya jalan di desktop runtime

`od export <file> --project <id> --format image --out <path>` ada di
daemon CLI dan kelihatan seperti jalur resmi untuk PNG. **Di server
tanpa desktop app, ini pasti gagal** dengan:

```
UPSTREAM_UNAVAILABLE: desktop renderer unavailable: connect ENOENT <path>
```

Komentar source-nya menulisnya polos: *"screenshot export is only
available in the desktop runtime"*. Export image/PDF/PPTX
menjalankan renderer Electron via unix socket
`/tmp/open-design/ipc/<namespace>/desktop.sock` — server headless tidak
mempunyai socket itu, dan error-nya tidak menjelaskan bahwa socket itulah
yang hilang.

**Jalan yang terbukti:** screenshot artifact HTML pakai binary chromium
headless (lihat "Screenshot artifak" di SKILL.md).

Kenapa bukan `od export` dengan Xvfb: Electron + Xvfb di host yang
sudah menjalankan daemon adalah tumpukan tiga proses untuk satu PNG.
Chromium playwright yang sudah di-cache adalah satu command.

## 2. Route `full_plan` — chain-nya tidak spawn dari klien MCP eksternal

`start_run` kadang membagi rencana dan produksi ke dua run. Tanda
`route: "full_plan"` di hasil `get_run`.

**Klien host** (opencode/VS Code memanggil OD dari dalam): run pertama
`succeeded`, `artifactCount: 0`, `deliverableValidation:
"no_artifact"`, dan `strategyTask.nextRunId` + `display.runIds`
memuat run produksi. **Itu bukan kegagalan** — poll ke runId baru itu.
Mulai `start_run` baru menggandakan kerja dan merusak rantai
percakapan.

**Klien MCP eksternal** (Hermes atau agent lain yang memanggil tool
`mcp__open_design__*`; payload run menunjukkan `clientType:
"external_mcp"`): **chain produksi tidak spawn otomatis.** Run pertama
terminal tanpa `nextRunId` dan tanpa artifact. Menunggu tidak
memproduksi apa-apa.

**Jalan yang terbukti (klien eksternal):** `start_run` sekali lagi di
conversation yang sama — prompt cache masih panas (cache hit ~79%),
murah — dengan perintah produksi eksplisit: *"ini perintah produksi,
bukan permintaan rencana — tulis artifact-nya di run ini, jangan emit
production-ready marker"*. Agen mengambil jalur bounded direct edit
dan artifact lahir di run itu.

Kenapa: agen OD mempertimbangkan rencana-vs-produksi setiap turn.
Prompt "buat screen X" dari klien host dijalankan host-nya sebagai
turn berikutnya; dari klien eksternal tidak ada turn berikutnya, jadi
prompt harus memerintahkan produksi dalam satu turn.

shortcut: 2 permintaan ulang untuk membuat artifact lahir — setelah
itu masalahnya ada di prompt, bukan di daemon; jangan restart daemon,
tidak membantu.

## 3. Polling — `status: running` + file statis bukan hang

`get_run` setiap 30–60 detik. File artifact yang tidak berubah
ukurannya dalam beberapa menit pertama adalah agen berpikir, bukan
hang — `cancel_run` karena tidak sabar membuang run yang sebagian
sudah benar. Sinyal nyata: log perubahan `events.jsonl` di
`<OD data dir>/runs/<runId>/events.jsonl` tumbuh (62KB → 100KB →
180KB teramati saat agen menulis CSS).

5–30 menit per run adalah rentang resmi. `agentExecutionDurationMs`
+ `totalDurationMs` di `executionDiagnostics` menunjukkan skala
sebenarnya saat run selesai.

## 4. Biaya inertness — plan/balance di `get_vela_login_status` bukan billing

`plan: free` / `balance: $0` di `get_vela_login_status` sering
dibaca sebagai "OD akan gagal di run besar". Login daemon itu
untuk autentikasi daemon, bukan billing inferensi. Inferensi ikut
model yang dikonfigurasi daemon
(`agentModels.<agentId>.model` di `<OD data dir>/app-config.json`).
Nilai `custom:omniroute:…` berarti arus ke endpoint sendiri.
Sampaikan hanya kalau mencurigakan (plan cloud aktif padahal yang
dipakai model local).

## 5. Nama tool yang salah — MCP lama vs MCP yang sebenarnya

Jangan mencari tool `register_open_design_artifact` /
`prepare_open_design_brief` / `check_open_design_artifact` /
`export_open_design_artifact` / `create_open_design_design_system`.
Itu nama dari MCP Open Design lama (legacy); MCP yang sebenarnya
memiliki `create_artifact`, `collect_brief`, `start_run`, `get_run`,
`get_artifact`. `collectionId` pun tidak ada — padanannya
`projectId`.

## 6. `.od-frames/` bukan penyimpanan hasil

Folder `.od-frames/` di project OD berisi template frame kosong
(`android.html`, `iphone.html`, `neutral.html`, `layout.css`) —
bukan preview bawaan artifact yang sudah dibuat. Jangan mengharapkan
PNG artifact di sana; screenshot sendiri.
