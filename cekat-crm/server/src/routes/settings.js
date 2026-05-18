import { Router } from 'express';
import db from '../db.js';

const router = Router();

const DEFAULTS = {
  working_hours_enabled: 0,
  work_start: '09:00',
  work_end: '17:00',
  work_days: '1,2,3,4,5',
  business_name: '',
  greeting: '',
};

router.get('/', (req, res) => {
  const row = db.prepare('SELECT * FROM settings WHERE user_id = ?').get(req.userId);
  res.json(row || { user_id: req.userId, ...DEFAULTS });
});

router.put('/', (req, res) => {
  const merged = { ...DEFAULTS, ...(req.body || {}) };
  const existing = db.prepare('SELECT user_id FROM settings WHERE user_id = ?').get(req.userId);

  if (existing) {
    db.prepare(`
      UPDATE settings
      SET working_hours_enabled = ?, work_start = ?, work_end = ?, work_days = ?,
          business_name = ?, greeting = ?, updated_at = datetime('now')
      WHERE user_id = ?
    `).run(
      merged.working_hours_enabled ? 1 : 0,
      merged.work_start,
      merged.work_end,
      merged.work_days,
      merged.business_name,
      merged.greeting,
      req.userId
    );
  } else {
    db.prepare(`
      INSERT INTO settings (user_id, working_hours_enabled, work_start, work_end, work_days, business_name, greeting)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(
      req.userId,
      merged.working_hours_enabled ? 1 : 0,
      merged.work_start,
      merged.work_end,
      merged.work_days,
      merged.business_name,
      merged.greeting
    );
  }
  res.json({ ok: true });
});

export default router;
