import { useEffect, useState } from 'react';
import { api } from '../api.js';

const PLACEHOLDER = `Contoh isi:

== Informasi Bisnis ==
Nama: Toko Maju Jaya
Jam buka: Senin-Sabtu 09.00-21.00, Minggu tutup
Lokasi: Jl. Merdeka No. 10, Jakarta

== Produk & Harga ==
- Kemeja pria: Rp 150.000
- Celana jeans: Rp 200.000
- Sepatu sneakers: Rp 350.000

== Pengiriman ==
Pengiriman pakai JNE/J&T. Ongkir ditanggung pembeli.
Estimasi: Jakarta 1-2 hari, luar kota 2-4 hari.

== Pembayaran ==
Transfer BCA 1234567890 a.n. Toko Maju Jaya

== Kebijakan ==
Retur barang dalam 3 hari jika ada kerusakan dari kami.`;

export default function Knowledge() {
  const [content, setContent] = useState('');
  const [updatedAt, setUpdatedAt] = useState(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    api('/knowledge').then((data) => {
      setContent(data.content || '');
      setUpdatedAt(data.updated_at);
    });
  }, []);

  async function save() {
    setSaving(true);
    try {
      await api('/knowledge', { method: 'PUT', body: { content } });
      setSavedAt(new Date());
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <h2>Knowledge Base (SOP AI Agent)</h2>
      <p style={{ color: 'var(--muted)', marginTop: -10 }}>
        Tulis SOP, harga, jam operasional, kebijakan, dan info bisnis lainnya. AI Agent akan menjawab pelanggan berdasarkan isi di sini.
        Makin lengkap → makin akurat AI-nya.
      </p>

      <div className="card">
        <textarea
          rows={22}
          style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 13 }}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={PLACEHOLDER}
        />
        <div style={{ display: 'flex', alignItems: 'center', marginTop: 12 }}>
          <div style={{ flex: 1, color: 'var(--muted)', fontSize: 12 }}>
            {updatedAt && <>Terakhir disimpan: {new Date(updatedAt + 'Z').toLocaleString('id-ID')}</>}
            {savedAt && <span style={{ color: 'var(--success)', marginLeft: 10 }}>✓ Tersimpan</span>}
          </div>
          <button className="primary" onClick={save} disabled={saving}>
            {saving ? 'Menyimpan...' : 'Simpan'}
          </button>
        </div>
      </div>
    </>
  );
}
