import { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Dashboard() {
  const [stats, setStats] = useState({ contacts: 0, conversations: 0, open: 0, resolved: 0, aiActive: 0 });

  useEffect(() => {
    Promise.all([api('/contacts'), api('/conversations')]).then(([contacts, conversations]) => {
      setStats({
        contacts: contacts.length,
        conversations: conversations.length,
        open: conversations.filter((c) => c.status === 'open').length,
        resolved: conversations.filter((c) => c.status === 'resolved').length,
        aiActive: conversations.filter((c) => c.ai_enabled).length,
      });
    });
  }, []);

  return (
    <>
      <h2>Dashboard</h2>
      <div className="stat-grid">
        <div className="stat">
          <div className="label">Total Kontak</div>
          <div className="value">{stats.contacts}</div>
        </div>
        <div className="stat">
          <div className="label">Percakapan Aktif</div>
          <div className="value">{stats.open}</div>
        </div>
        <div className="stat">
          <div className="label">Selesai</div>
          <div className="value" style={{ color: 'var(--success)' }}>{stats.resolved}</div>
        </div>
        <div className="stat">
          <div className="label">AI Agent Aktif</div>
          <div className="value">{stats.aiActive}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h3 style={{ marginTop: 0 }}>Selamat datang di Cekat CRM 👋</h3>
        <p>Langkah cepat untuk mulai:</p>
        <ol>
          <li>Buka <strong>Knowledge Base</strong>, isi SOP & info bisnis Anda.</li>
          <li>Tambahkan kontak pelanggan di menu <strong>Kontak</strong>.</li>
          <li>Buka <strong>Inbox</strong>, mulai percakapan, dan aktifkan AI Agent.</li>
          <li>Coba kirim pesan dari panel "Simulasi Pelanggan" — AI akan membalas otomatis.</li>
        </ol>
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>
          Integrasi WhatsApp/Instagram belum ada di MVP ini — fokus dulu validasi alur jualan-via-AI ke 3-5 klien pilot.
        </p>
      </div>
    </>
  );
}
