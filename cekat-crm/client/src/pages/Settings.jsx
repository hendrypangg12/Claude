import { useEffect, useState } from 'react';
import { api } from '../api.js';

const DAYS = [
  { value: 1, label: 'Senin' },
  { value: 2, label: 'Selasa' },
  { value: 3, label: 'Rabu' },
  { value: 4, label: 'Kamis' },
  { value: 5, label: 'Jumat' },
  { value: 6, label: 'Sabtu' },
  { value: 0, label: 'Minggu' },
];

export default function Settings() {
  const [s, setS] = useState(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    api('/settings').then((data) => {
      setS({
        working_hours_enabled: !!data.working_hours_enabled,
        work_start: data.work_start || '09:00',
        work_end: data.work_end || '17:00',
        work_days: (data.work_days || '1,2,3,4,5').split(',').map((d) => parseInt(d, 10)),
        business_name: data.business_name || '',
        greeting: data.greeting || '',
      });
    });
  }, []);

  function toggleDay(d) {
    const has = s.work_days.includes(d);
    setS({
      ...s,
      work_days: has ? s.work_days.filter((x) => x !== d) : [...s.work_days, d].sort(),
    });
  }

  async function save() {
    setSaving(true);
    try {
      await api('/settings', {
        method: 'PUT',
        body: { ...s, work_days: s.work_days.join(',') },
      });
      setSavedAt(new Date());
    } finally {
      setSaving(false);
    }
  }

  if (!s) return null;

  return (
    <>
      <h2>Pengaturan</h2>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Informasi Bisnis</h3>
        <div className="form-row">
          <label>Nama bisnis (untuk salam AI)</label>
          <input
            value={s.business_name}
            onChange={(e) => setS({ ...s, business_name: e.target.value })}
            placeholder="Toko Maju Jaya"
          />
        </div>
        <div className="form-row">
          <label>Pesan sambutan AI (opsional, otomatis dikirim ke pelanggan baru)</label>
          <textarea
            value={s.greeting}
            onChange={(e) => setS({ ...s, greeting: e.target.value })}
            placeholder="Halo! Terima kasih sudah menghubungi kami. Ada yang bisa kami bantu?"
            rows={3}
          />
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Jam Kerja AI</h3>
        <p style={{ color: 'var(--muted)', marginTop: 0 }}>
          Saat aktif: <strong>dalam jam kerja</strong> chat dibalas tim admin manual.{' '}
          <strong>Di luar jam kerja</strong> AI otomatis membalas. Mirip alur Cekat.AI.
        </p>

        <div className="form-row" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <input
            type="checkbox"
            id="wh-enabled"
            style={{ width: 'auto' }}
            checked={s.working_hours_enabled}
            onChange={(e) => setS({ ...s, working_hours_enabled: e.target.checked })}
          />
          <label htmlFor="wh-enabled" style={{ margin: 0 }}>
            Aktifkan jam kerja AI
          </label>
        </div>

        {s.working_hours_enabled && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div className="form-row">
                <label>Jam mulai kerja</label>
                <input
                  type="time"
                  value={s.work_start}
                  onChange={(e) => setS({ ...s, work_start: e.target.value })}
                />
              </div>
              <div className="form-row">
                <label>Jam selesai kerja</label>
                <input
                  type="time"
                  value={s.work_end}
                  onChange={(e) => setS({ ...s, work_end: e.target.value })}
                />
              </div>
            </div>
            <div className="form-row">
              <label>Hari kerja</label>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {DAYS.map((d) => (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => toggleDay(d.value)}
                    className={s.work_days.includes(d.value) ? 'primary' : ''}
                    style={{ padding: '6px 12px', fontSize: 12 }}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 8 }}>
                Zona waktu: WIB (Asia/Jakarta)
              </div>
            </div>
          </>
        )}

        <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="primary" onClick={save} disabled={saving}>
            {saving ? 'Menyimpan...' : 'Simpan Pengaturan'}
          </button>
          {savedAt && <span style={{ color: 'var(--success)', fontSize: 13 }}>✓ Tersimpan</span>}
        </div>
      </div>
    </>
  );
}
