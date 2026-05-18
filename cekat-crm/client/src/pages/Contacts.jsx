import { useEffect, useState } from 'react';
import { api } from '../api.js';

const EMPTY = { name: '', phone: '', email: '', tag: '', notes: '' };

export default function Contacts() {
  const [contacts, setContacts] = useState([]);
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');

  async function load() {
    setContacts(await api('/contacts'));
  }

  useEffect(() => { load(); }, []);

  function openNew() {
    setEditing('new');
    setForm(EMPTY);
    setError('');
  }
  function openEdit(c) {
    setEditing(c.id);
    setForm({ name: c.name, phone: c.phone || '', email: c.email || '', tag: c.tag || '', notes: c.notes || '' });
    setError('');
  }

  async function save(e) {
    e.preventDefault();
    setError('');
    try {
      if (editing === 'new') {
        await api('/contacts', { method: 'POST', body: form });
      } else {
        await api(`/contacts/${editing}`, { method: 'PUT', body: form });
      }
      setEditing(null);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(id) {
    if (!confirm('Hapus kontak ini? Percakapan terkait juga ikut terhapus.')) return;
    await api(`/contacts/${id}`, { method: 'DELETE' });
    await load();
  }

  const filtered = contacts.filter((c) => {
    const q = query.toLowerCase();
    return !q || c.name.toLowerCase().includes(q) || (c.phone || '').includes(q) || (c.email || '').toLowerCase().includes(q);
  });

  return (
    <>
      <h2>Kontak Pelanggan</h2>
      <div className="toolbar">
        <input placeholder="Cari nama, no HP, email..." value={query} onChange={(e) => setQuery(e.target.value)} />
        <div className="spacer" />
        <button className="primary" onClick={openNew}>+ Tambah Kontak</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="big">👥</div>
            <div>Belum ada kontak.</div>
            <div style={{ marginTop: 12 }}>
              <button className="primary" onClick={openNew}>Tambah kontak pertama</button>
            </div>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nama</th>
                <th>Telepon</th>
                <th>Email</th>
                <th>Tag</th>
                <th style={{ width: 140 }}>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id}>
                  <td><strong>{c.name}</strong>{c.notes && <div style={{ fontSize: 12, color: 'var(--muted)' }}>{c.notes}</div>}</td>
                  <td>{c.phone || '-'}</td>
                  <td>{c.email || '-'}</td>
                  <td>{c.tag ? <span className="tag" style={{ background: 'var(--primary-light)', color: 'var(--primary)', padding: '2px 8px', borderRadius: 4, fontSize: 11 }}>{c.tag}</span> : '-'}</td>
                  <td>
                    <button onClick={() => openEdit(c)} style={{ padding: '4px 8px', fontSize: 12 }}>Edit</button>{' '}
                    <button onClick={() => remove(c.id)} className="danger" style={{ padding: '4px 8px', fontSize: 12 }}>Hapus</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editing !== null && (
        <div className="modal-backdrop" onClick={() => setEditing(null)}>
          <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
            <h3>{editing === 'new' ? 'Tambah Kontak' : 'Edit Kontak'}</h3>
            {error && <div className="error-banner">{error}</div>}
            <div className="form-row">
              <label>Nama *</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="form-row">
              <label>No. Telepon / WA</label>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="62812..." />
            </div>
            <div className="form-row">
              <label>Email</label>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
            <div className="form-row">
              <label>Tag (contoh: VIP, Hot Lead)</label>
              <input value={form.tag} onChange={(e) => setForm({ ...form, tag: e.target.value })} />
            </div>
            <div className="form-row">
              <label>Catatan</label>
              <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </div>
            <div className="modal-actions">
              <button type="button" onClick={() => setEditing(null)}>Batal</button>
              <button type="submit" className="primary">Simpan</button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
