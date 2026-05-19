# BerBisnis (MVP)

Aplikasi CRM omnichannel + AI Agent mini untuk UMKM Indonesia. AI Agent pakai Claude Haiku 4.5 dengan prompt caching untuk knowledge base.

## Fitur

- 🔐 Auth (register / login, JWT)
- 👥 Manajemen kontak (CRUD + tag + catatan)
- 📥 **Import kontak via CSV** (bulk, sampai 500 per file)
- 💬 Inbox percakapan (list + chat view, filter Aktif/Selesai)
- 🤖 AI Agent otomatis balas pesan pelanggan (Claude Haiku 4.5)
- 🧠 **AI Suggest** — admin minta saran balasan AI, edit, lalu kirim
- ⚡ **Quick Reply Templates** — balasan tersimpan, klik untuk insert
- 📚 Knowledge Base editor (SOP bisnis, jadi acuan AI)
- 🕐 **Jam Kerja AI** — AI hanya balas di luar jam kerja, dalam jam kerja admin handle
- 👋 **Auto-greeting** — sapaan otomatis untuk pelanggan baru
- 📱 **Integrasi WhatsApp** via Twilio Sandbox (opsional)
- 📊 **Dashboard analytics** — grafik aktivitas 14 hari, distribusi balasan, top pelanggan, insight otomatis
- 🎭 **Personalisasi tone AI** — 4 karakter (Ramah/Formal/Santai/Singkat) per bisnis
- 📱 **Mobile responsive** — bisa demo dari HP

## Stack

- **Server**: Node.js + Express + SQLite (`better-sqlite3`) + JWT + bcrypt + `@anthropic-ai/sdk` + `twilio`
- **Client**: React + Vite + React Router

## Setup (sekali saja)

Prasyarat: **Node.js 20+**.

```bash
# 1. Install dependencies
cd cekat-crm/server && npm install
cd ../client && npm install

# 2. Setup env file untuk server
cd ../server
cp .env.example .env
# Edit .env: minimal ganti JWT_SECRET (string panjang acak), isi ANTHROPIC_API_KEY
```

`ANTHROPIC_API_KEY` di https://console.anthropic.com.

## Jalankan

Buka 2 terminal:

```bash
# Terminal 1 — backend
cd cekat-crm/server && npm run dev   # http://localhost:3001

# Terminal 2 — frontend
cd cekat-crm/client && npm run dev   # http://localhost:5173
```

Buka http://localhost:5173 di browser, klik "Daftar" untuk buat akun.

## Alur Pemakaian

1. **Daftar akun** → otomatis masuk ke aplikasi
2. **Pengaturan**: isi nama bisnis, pesan sambutan, set jam kerja AI, buat template balasan cepat
3. **Knowledge Base**: tulis SOP, harga, jam buka, kebijakan retur, dll
4. **Kontak**: tambah manual atau import dari CSV
5. **Inbox**: mulai percakapan, ketik pesan sebagai pelanggan (panel kanan) atau balas sebagai admin (tengah)
6. Coba "🤖 Saran AI" — AI saranin balasan berdasarkan riwayat chat, admin edit lalu kirim

## Integrasi WhatsApp via Twilio (opsional)

Untuk demo ke calon klien dengan WhatsApp asli (sandbox, gratis):

### 1. Setup di Twilio

1. Daftar akun di https://www.twilio.com (free trial dapat $15 kredit)
2. Buka https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
3. Aktifkan WhatsApp Sandbox — Twilio kasih nomor `+1 415 523 8886` dan kode unik
4. Di WhatsApp Anda, kirim pesan "join <kode>" ke nomor sandbox itu

### 2. Expose server local ke internet (pakai ngrok)

```bash
# Install ngrok di laptop: https://ngrok.com/download
ngrok http 3001
```

Catat URL yang muncul (mis. `https://abc123.ngrok-free.app`).

### 3. Set webhook di Twilio

Di halaman sandbox Twilio, set field **"WHEN A MESSAGE COMES IN"** ke:
```
https://<ngrok-url>/api/webhooks/twilio/whatsapp
```
Method: **HTTP POST**

### 4. Update `server/.env`

```bash
TWILIO_ACCOUNT_SID=AC...          # dari Twilio Console
TWILIO_AUTH_TOKEN=...             # dari Twilio Console
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_DEFAULT_USER_ID=1          # ID user CRM Anda (cek di DB atau buat akun pertama)
TWILIO_WEBHOOK_URL=https://abc123.ngrok-free.app
TWILIO_SKIP_VERIFY=true           # untuk dev, set false di produksi
```

Restart server. Sekarang WhatsApp yang join sandbox → masuk ke Inbox CRM Anda → AI auto-reply (kalau di luar jam kerja) atau admin balas manual → reply terkirim balik ke WhatsApp via Twilio.

⚠️ **Limit sandbox Twilio**: hanya nomor yang sudah join via "join <kode>" yang bisa kirim/terima. Untuk produksi, perlu beli nomor WhatsApp Business resmi (lewat Twilio atau Meta).

## Struktur

```
cekat-crm/
├── server/
│   ├── src/
│   │   ├── index.js
│   │   ├── db.js
│   │   ├── middleware/auth.js
│   │   ├── lib/
│   │   │   ├── ai-agent.js          # Claude API + working hours logic
│   │   │   └── channels.js          # outbound WhatsApp via Twilio
│   │   └── routes/
│   │       ├── auth.js
│   │       ├── contacts.js          # + /bulk untuk CSV import
│   │       ├── conversations.js     # + /ai-suggest, auto-greeting
│   │       ├── knowledge.js
│   │       ├── settings.js
│   │       ├── quick-replies.js
│   │       └── twilio-webhook.js    # inbound WhatsApp dari Twilio
│   ├── data.db                      # SQLite (auto-generated, gitignored)
│   └── .env                         # gitignored
└── client/
    └── src/
        ├── api.js
        ├── App.jsx
        ├── components/AppLayout.jsx
        └── pages/
            ├── Login.jsx, Register.jsx
            ├── Inbox.jsx            # + AI suggest, quick replies
            ├── Contacts.jsx         # + CSV import
            ├── Knowledge.jsx
            ├── Settings.jsx         # + quick replies CRUD
            └── Dashboard.jsx
```

## Biaya AI

Pakai Claude Haiku 4.5 (`claude-haiku-4-5`):
- Input: $1 per 1 juta token (~Rp 16.000)
- Output: $5 per 1 juta token (~Rp 80.000)
- Prompt caching aktif untuk knowledge base → 90% hemat untuk request ke-2 dst

Estimasi: 1 chat (10 turn) ≈ Rp 50-200 tergantung panjang KB.

## Catatan Bisnis

Sebelum scaling fitur:
1. **Validasi dulu ke 3-5 bisnis pilot** — apakah mau bayar?
2. **Bedakan dari SaaS chatbot besar** — pilih niche (mis. khusus dental clinic) atau harga lebih murah
3. **WhatsApp resmi (Meta Business API)** butuh verifikasi bisnis + setup tidak instan
