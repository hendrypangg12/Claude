# Cekat CRM (MVP)

Aplikasi CRM omnichannel + AI Agent mini, inspired by Cekat.AI. Single-tenant per akun, AI Agent pakai Claude Haiku 4.5 dengan prompt caching untuk knowledge base.

## Fitur MVP

- Auth (register / login, JWT)
- Manajemen kontak pelanggan (CRUD + tag + catatan)
- Inbox percakapan (list + chat view, kirim dari sisi admin atau pelanggan)
- AI Agent otomatis membalas pesan pelanggan, basis knowledge base per akun
- Knowledge Base editor (isi SOP, harga, jam buka, dll — AI pakai ini untuk menjawab)
- Dashboard ringkasan
- Simulator chat (belum ada integrasi WhatsApp/Instagram asli)

## Stack

- **Server**: Node.js + Express + SQLite (`better-sqlite3`) + JWT + bcrypt + `@anthropic-ai/sdk`
- **Client**: React + Vite + React Router (single page app)

## Setup (sekali saja)

Prasyarat: **Node.js 20+** terinstall.

```bash
# 1. Install dependencies (di 2 folder)
cd cekat-crm/server && npm install
cd ../client && npm install

# 2. Setup env file untuk server
cd ../server
cp .env.example .env
# Edit .env: minimal ganti JWT_SECRET (string panjang acak), isi ANTHROPIC_API_KEY
```

Dapatkan `ANTHROPIC_API_KEY` di https://console.anthropic.com (bayar pakai kartu kredit).

## Jalankan

Buka 2 terminal:

```bash
# Terminal 1 — backend
cd cekat-crm/server
npm run dev
# → http://localhost:3001

# Terminal 2 — frontend
cd cekat-crm/client
npm run dev
# → http://localhost:5173
```

Buka http://localhost:5173 di browser, klik "Daftar" untuk buat akun.

## Cara Pakai

1. **Daftar akun** → otomatis masuk ke aplikasi
2. **Knowledge Base**: tulis SOP bisnis Anda (jam buka, harga, kebijakan retur, dll)
3. **Kontak**: tambah beberapa kontak pelanggan dummy
4. **Inbox**: klik "+ Baru" → pilih kontak → mulai percakapan
5. **Simulasi pelanggan** di panel kanan — ketik pesan sebagai pelanggan, AI akan balas otomatis (jika toggle "AI Agent aktif" menyala)
6. Anda juga bisa balas manual sebagai admin dari panel tengah

## Struktur

```
cekat-crm/
├── server/
│   ├── src/
│   │   ├── index.js            # Express entry
│   │   ├── db.js               # SQLite + migrasi tabel
│   │   ├── middleware/auth.js  # JWT verifier
│   │   └── routes/             # auth, contacts, conversations, knowledge
│   ├── data.db                 # SQLite file (auto-generated, gitignored)
│   └── .env                    # Secret (gitignored)
└── client/
    └── src/
        ├── api.js              # fetch wrapper + token storage
        ├── App.jsx             # router
        ├── components/         # AppLayout
        └── pages/              # Login, Register, Inbox, Contacts, Knowledge, Dashboard
```

## Biaya AI

Pakai Claude Haiku 4.5:
- Input: $1 per 1 juta token (~Rp 16.000)
- Output: $5 per 1 juta token (~Rp 80.000)
- Prompt caching aktif untuk knowledge base → 90% hemat untuk request ke-2 dan seterusnya

Estimasi: 1 chat (10 turn) ≈ Rp 50-200 tergantung panjang knowledge base.

## Roadmap (kalau mau dilanjut)

- [ ] Integrasi WhatsApp via Twilio sandbox
- [ ] Multi-user per akun (tim CS dengan role berbeda)
- [ ] Visual flow designer (drag & drop alur chat)
- [ ] Jam kerja AI (auto-handoff ke human di jam tertentu)
- [ ] API integration (cek ongkir, booking, dll)
- [ ] Analytics: conversion rate, avg response time
- [ ] Multi-tenant (1 server untuk banyak bisnis)

## Catatan Bisnis

Sebelum scaling fitur:
1. **Validasi dulu ke 3-5 bisnis pilot** — apakah mereka mau bayar?
2. **Kompetitor Cekat.AI sudah mature** — bedakan dengan niche industri (misal: hanya untuk dental clinic, hanya untuk F&B) atau harga
3. **Untuk WhatsApp resmi (Meta Business API)** perlu verifikasi bisnis + setup tidak instan, anggarkan Rp 1-3 jt setup awal
