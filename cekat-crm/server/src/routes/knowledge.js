import { Router } from 'express';
import db from '../db.js';

const router = Router();

router.get('/', (req, res) => {
  const row = db.prepare('SELECT content, updated_at FROM knowledge WHERE user_id = ?').get(req.userId);
  res.json(row || { content: '', updated_at: null });
});

router.put('/', (req, res) => {
  const { content } = req.body || {};
  if (typeof content !== 'string') return res.status(400).json({ error: 'content harus string' });
  const existing = db.prepare('SELECT id FROM knowledge WHERE user_id = ?').get(req.userId);
  if (existing) {
    db.prepare(
      "UPDATE knowledge SET content = ?, updated_at = datetime('now') WHERE user_id = ?"
    ).run(content, req.userId);
  } else {
    db.prepare(
      'INSERT INTO knowledge (user_id, content) VALUES (?, ?)'
    ).run(req.userId, content);
  }
  res.json({ ok: true });
});

export default router;
