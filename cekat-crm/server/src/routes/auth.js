import { Router } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import db from '../db.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();

router.post('/register', (req, res) => {
  const { email, name, password } = req.body || {};
  if (!email || !name || !password) {
    return res.status(400).json({ error: 'email, name, password wajib diisi' });
  }
  if (password.length < 6) {
    return res.status(400).json({ error: 'Password minimal 6 karakter' });
  }
  const existing = db.prepare('SELECT id FROM users WHERE email = ?').get(email);
  if (existing) return res.status(409).json({ error: 'Email sudah terdaftar' });

  const hash = bcrypt.hashSync(password, 10);
  const info = db.prepare(
    'INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)'
  ).run(email, name, hash);

  const token = jwt.sign({ sub: info.lastInsertRowid }, process.env.JWT_SECRET, { expiresIn: '7d' });
  res.json({ token, user: { id: info.lastInsertRowid, email, name } });
});

router.post('/login', (req, res) => {
  const { email, password } = req.body || {};
  const user = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
  if (!user || !bcrypt.compareSync(password || '', user.password_hash)) {
    return res.status(401).json({ error: 'Email atau password salah' });
  }
  const token = jwt.sign({ sub: user.id }, process.env.JWT_SECRET, { expiresIn: '7d' });
  res.json({ token, user: { id: user.id, email: user.email, name: user.name } });
});

router.get('/me', requireAuth, (req, res) => {
  const user = db.prepare('SELECT id, email, name FROM users WHERE id = ?').get(req.userId);
  res.json({ user });
});

export default router;
