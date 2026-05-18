import { Router } from 'express';
import db from '../db.js';

const router = Router();

router.get('/', (req, res) => {
  const rows = db.prepare(
    'SELECT * FROM quick_replies WHERE user_id = ? ORDER BY id ASC'
  ).all(req.userId);
  res.json(rows);
});

router.post('/', (req, res) => {
  const { label, body } = req.body || {};
  if (!label || !body) return res.status(400).json({ error: 'label dan body wajib diisi' });
  const info = db.prepare(
    'INSERT INTO quick_replies (user_id, label, body) VALUES (?, ?, ?)'
  ).run(req.userId, label.trim(), body.trim());
  res.json({ id: info.lastInsertRowid });
});

router.put('/:id', (req, res) => {
  const { label, body } = req.body || {};
  const result = db.prepare(
    'UPDATE quick_replies SET label = ?, body = ? WHERE id = ? AND user_id = ?'
  ).run(label, body, req.params.id, req.userId);
  if (!result.changes) return res.status(404).json({ error: 'Template tidak ditemukan' });
  res.json({ ok: true });
});

router.delete('/:id', (req, res) => {
  const result = db.prepare(
    'DELETE FROM quick_replies WHERE id = ? AND user_id = ?'
  ).run(req.params.id, req.userId);
  if (!result.changes) return res.status(404).json({ error: 'Template tidak ditemukan' });
  res.json({ ok: true });
});

export default router;
