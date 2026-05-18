import { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api('/analytics').then(setData);
  }, []);

  if (!data) return <div>Memuat...</div>;
  const t = data.totals;

  return (
    <>
      <h2>Dashboard</h2>

      <div className="stat-grid">
        <StatCard label="Total Kontak" value={t.contacts} icon="👥" />
        <StatCard label="Percakapan Aktif" value={t.open} icon="💬" />
        <StatCard label="Selesai" value={t.resolved} icon="✅" color="var(--success)" />
        <StatCard label="Total Pesan" value={t.messages} icon="📨" />
      </div>

      <div className="dash-grid">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Aktivitas Pesan (14 Hari Terakhir)</h3>
          {data.daily_messages.length === 0 ? (
            <EmptyChart />
          ) : (
            <MessageChart data={data.daily_messages} />
          )}
          <ChartLegend />
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Distribusi Balasan</h3>
          <ReplyDistribution
            ai={t.messages_ai}
            agent={t.messages_agent}
            customer={t.messages_customer}
          />
          <div className="ai-share-highlight">
            <div className="ai-share-num">{t.ai_share_percent}%</div>
            <div className="ai-share-label">balasan otomatis oleh AI</div>
            <div className="ai-share-sublabel">
              {t.ai_share_percent >= 50
                ? '✨ AI handle mayoritas — tim CS bisa fokus ke kasus kompleks'
                : 'AI mulai berkontribusi — pertajam knowledge base untuk hasil lebih baik'}
            </div>
          </div>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Pelanggan Paling Aktif</h3>
          {data.top_contacts.length === 0 ? (
            <div style={{ color: 'var(--muted)', padding: 20, textAlign: 'center' }}>
              Belum ada percakapan
            </div>
          ) : (
            <table style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Nama</th>
                  <th>Telepon</th>
                  <th style={{ textAlign: 'right' }}>Pesan</th>
                </tr>
              </thead>
              <tbody>
                {data.top_contacts.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <strong>{c.name}</strong>
                      {c.tag && <span className="tag" style={{ marginLeft: 6 }}>{c.tag}</span>}
                    </td>
                    <td>{c.phone || '-'}</td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>{c.message_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card insight-card">
          <h3 style={{ marginTop: 0 }}>💡 Insight & Saran</h3>
          <Insights totals={t} />
        </div>
      </div>
    </>
  );
}

function StatCard({ label, value, icon, color }) {
  return (
    <div className="stat">
      <div className="label">
        <span style={{ marginRight: 6 }}>{icon}</span>
        {label}
      </div>
      <div className="value" style={color ? { color } : undefined}>{value}</div>
    </div>
  );
}

function MessageChart({ data }) {
  // Fill missing days for last 14 days so chart shows a continuous timeline
  const today = new Date();
  const days = [];
  for (let i = 13; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const found = data.find((r) => r.day === key);
    days.push({
      day: key,
      label: d.getDate() + '/' + (d.getMonth() + 1),
      customer: found?.customer || 0,
      agent: found?.agent || 0,
      ai: found?.ai || 0,
    });
  }
  const max = Math.max(1, ...days.map((d) => d.customer + d.agent + d.ai));

  return (
    <div className="chart-bars">
      {days.map((d) => {
        const total = d.customer + d.agent + d.ai;
        const pct = (n) => (total > 0 ? (n / max) * 100 : 0);
        return (
          <div key={d.day} className="chart-col" title={`${d.label}: ${total} pesan`}>
            <div className="bar-stack">
              <div className="bar bar-customer" style={{ height: pct(d.customer) + '%' }} />
              <div className="bar bar-ai" style={{ height: pct(d.ai) + '%' }} />
              <div className="bar bar-agent" style={{ height: pct(d.agent) + '%' }} />
            </div>
            <div className="chart-label">{d.label}</div>
          </div>
        );
      })}
    </div>
  );
}

function ChartLegend() {
  return (
    <div className="chart-legend">
      <span><i className="dot bar-customer" /> Pelanggan</span>
      <span><i className="dot bar-ai" /> AI</span>
      <span><i className="dot bar-agent" /> Admin</span>
    </div>
  );
}

function EmptyChart() {
  return (
    <div style={{ textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
      <div style={{ fontSize: 36 }}>📊</div>
      <div>Belum ada data pesan dalam 14 hari terakhir.</div>
    </div>
  );
}

function ReplyDistribution({ ai, agent, customer }) {
  const total = ai + agent + customer;
  if (total === 0) return <div style={{ color: 'var(--muted)', padding: 20, textAlign: 'center' }}>Belum ada pesan</div>;
  const pct = (n) => Math.round((n / total) * 100);
  return (
    <div className="reply-dist">
      <DistRow label="Pelanggan" value={customer} pct={pct(customer)} className="bar-customer" />
      <DistRow label="AI Agent" value={ai} pct={pct(ai)} className="bar-ai" />
      <DistRow label="Admin Manual" value={agent} pct={pct(agent)} className="bar-agent" />
    </div>
  );
}

function DistRow({ label, value, pct, className }) {
  return (
    <div className="dist-row">
      <div className="dist-label">{label}</div>
      <div className="dist-bar-wrap">
        <div className={'dist-bar ' + className} style={{ width: pct + '%' }} />
      </div>
      <div className="dist-num">{value} <small>({pct}%)</small></div>
    </div>
  );
}

function Insights({ totals }) {
  const tips = [];
  if (totals.contacts === 0) {
    tips.push({ icon: '👋', text: 'Mulai dengan menambah kontak pelanggan di menu Kontak, atau import via CSV.' });
  }
  if (totals.contacts > 0 && totals.conversations === 0) {
    tips.push({ icon: '💬', text: 'Buka Inbox dan mulai percakapan dengan kontak yang sudah ada.' });
  }
  if (totals.conversations > 0 && totals.messages_ai === 0) {
    tips.push({ icon: '🤖', text: 'AI belum pernah balas — pastikan toggle "AI Agent aktif" menyala di percakapan, dan ANTHROPIC_API_KEY sudah di-set.' });
  }
  if (totals.ai_share_percent < 30 && totals.messages_ai > 0) {
    tips.push({ icon: '📚', text: 'Knowledge base mungkin perlu diperluas — AI hanya handle ' + totals.ai_share_percent + '% balasan. Tambahkan info SOP/harga/jadwal yang sering ditanya.' });
  }
  if (totals.ai_share_percent >= 70) {
    tips.push({ icon: '🎉', text: 'AI handle ' + totals.ai_share_percent + '% — tim Anda bisa fokus closing & kasus rumit.' });
  }
  if (totals.open > 20) {
    tips.push({ icon: '⚠️', text: 'Ada ' + totals.open + ' percakapan aktif. Jangan lupa tandai "Selesai" yang sudah tuntas.' });
  }
  if (tips.length === 0) {
    tips.push({ icon: '✅', text: 'Semua berjalan baik. Lanjutkan dan pantau metrik di sini secara berkala.' });
  }
  return (
    <ul className="insight-list">
      {tips.map((t, i) => (
        <li key={i}><span className="insight-icon">{t.icon}</span> {t.text}</li>
      ))}
    </ul>
  );
}
