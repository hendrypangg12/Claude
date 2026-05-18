import { Router } from 'express';
import db from '../db.js';

const router = Router();

router.get('/', (req, res) => {
  const rows = db.prepare(
    'SELECT * FROM contacts WHERE user_id = ? ORDER BY created_at DESC'
  ).all(req.userId);
  res.json(rows);
});

router.post('/', (req, res) => {
  const { name, phone, email, tag, notes } = req.body || {};
  if (!name) return res.status(400).json({ error: 'name wajib diisi' });
  const info = db.prepare(
    'INSERT INTO contacts (user_id, name, phone, email, tag, notes) VALUES (?, ?, ?, ?, ?, ?)'
  ).run(req.userId, name, phone || null, email || null, tag || null, notes || null);
  res.json({ id: info.lastInsertRowid });
});

router.put('/:id', (req, res) => {
  const { name, phone, email, tag, notes } = req.body || {};
  const result = db.prepare(
    'UPDATE contacts SET name = ?, phone = ?, email = ?, tag = ?, notes = ? WHERE id = ? AND user_id = ?'
  ).run(name, phone, email, tag, notes, req.params.id, req.userId);
  if (!result.changes) return res.status(404).json({ error: 'Kontak tidak ditemukan' });
  res.json({ ok: true });
});

router.post('/bulk', (req, res) => {
  const { contacts } = req.body || {};
  if (!Array.isArray(contacts) || contacts.length === 0) {
    return res.status(400).json({ error: 'contacts harus berupa array (tidak kosong)' });
  }
  if (contacts.length > 500) {
    return res.status(400).json({ error: 'Maksimal 500 kontak per import. Bagi jadi beberapa file.' });
  }

  const stmt = db.prepare(
    'INSERT INTO contacts (user_id, name, phone, email, tag, notes) VALUES (?, ?, ?, ?, ?, ?)'
  );
  const insertMany = db.transaction((rows) => {
    let inserted = 0;
    for (const c of rows) {
      if (!c.name?.trim()) continue;
      stmt.run(
        req.userId,
        c.name.trim(),
        c.phone?.trim() || null,
        c.email?.trim() || null,
        c.tag?.trim() || null,
        c.notes?.trim() || null
      );
      inserted++;
    }
    return inserted;
  });

  const inserted = insertMany(contacts);
  res.json({ ok: true, inserted, skipped: contacts.length - inserted });
});

router.delete('/:id', (req, res) => {
  const result = db.prepare(
    'DELETE FROM contacts WHERE id = ? AND user_id = ?'
  ).run(req.params.id, req.userId);
  if (!result.changes) return res.status(404).json({ error: 'Kontak tidak ditemukan' });
  res.json({ ok: true });
});

export default router;
