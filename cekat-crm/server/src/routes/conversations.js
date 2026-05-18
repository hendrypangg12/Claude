import { Router } from 'express';
import db from '../db.js';
import { shouldAIRespond, generateAIReply } from '../lib/ai-agent.js';
import { sendToChannel } from '../lib/channels.js';

const router = Router();

router.get('/', (req, res) => {
  const status = req.query.status;
  const params = [req.userId];
  let where = 'WHERE c.user_id = ?';
  if (status === 'open' || status === 'resolved') {
    where += ' AND c.status = ?';
    params.push(status);
  }
  const rows = db.prepare(`
    SELECT c.id, c.contact_id, c.channel, c.ai_enabled, c.status, c.updated_at,
           ct.name AS contact_name, ct.phone AS contact_phone, ct.tag AS contact_tag,
           (SELECT body FROM messages WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) AS last_message,
           (SELECT sender FROM messages WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) AS last_sender,
           (SELECT created_at FROM messages WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) AS last_at
    FROM conversations c
    JOIN contacts ct ON ct.id = c.contact_id
    ${where}
    ORDER BY COALESCE(last_at, c.updated_at) DESC
  `).all(...params);
  res.json(rows);
});

router.post('/', (req, res) => {
  const { contact_id } = req.body || {};
  if (!contact_id) return res.status(400).json({ error: 'contact_id wajib diisi' });
  const contact = db.prepare(
    'SELECT id FROM contacts WHERE id = ? AND user_id = ?'
  ).get(contact_id, req.userId);
  if (!contact) return res.status(404).json({ error: 'Kontak tidak ditemukan' });

  const existing = db.prepare(
    'SELECT id FROM conversations WHERE user_id = ? AND contact_id = ?'
  ).get(req.userId, contact_id);
  if (existing) return res.json({ id: existing.id });

  const info = db.prepare(
    'INSERT INTO conversations (user_id, contact_id) VALUES (?, ?)'
  ).run(req.userId, contact_id);

  // Auto-greeting: kalau settings.greeting ada isinya, kirim sebagai pesan AI pertama
  const settings = db.prepare('SELECT greeting FROM settings WHERE user_id = ?').get(req.userId);
  if (settings?.greeting?.trim()) {
    db.prepare(
      'INSERT INTO messages (conversation_id, sender, body) VALUES (?, ?, ?)'
    ).run(info.lastInsertRowid, 'ai', settings.greeting.trim());
  }

  res.json({ id: info.lastInsertRowid });
});

router.get('/:id/messages', (req, res) => {
  const conv = db.prepare(
    'SELECT id FROM conversations WHERE id = ? AND user_id = ?'
  ).get(req.params.id, req.userId);
  if (!conv) return res.status(404).json({ error: 'Percakapan tidak ditemukan' });
  const rows = db.prepare(
    'SELECT id, sender, body, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC'
  ).all(req.params.id);
  res.json(rows);
});

router.post('/:id/messages', async (req, res) => {
  const { body, sender } = req.body || {};
  if (!body || !sender) return res.status(400).json({ error: 'body dan sender wajib diisi' });
  if (!['customer', 'agent'].includes(sender)) {
    return res.status(400).json({ error: 'sender harus "customer" atau "agent"' });
  }

  const conv = db.prepare(
    'SELECT * FROM conversations WHERE id = ? AND user_id = ?'
  ).get(req.params.id, req.userId);
  if (!conv) return res.status(404).json({ error: 'Percakapan tidak ditemukan' });

  db.prepare(
    'INSERT INTO messages (conversation_id, sender, body) VALUES (?, ?, ?)'
  ).run(conv.id, sender, body);
  db.prepare("UPDATE conversations SET updated_at = datetime('now') WHERE id = ?").run(conv.id);

  // Forward outgoing admin messages back to the channel (e.g. WhatsApp via Twilio)
  if (sender === 'agent') {
    sendToChannel(conv, body).catch((e) => console.error('Channel send failed:', e.message));
  }

  let aiReply = null;
  if (sender === 'customer' && conv.ai_enabled && shouldAIRespond(req.userId)) {
    try {
      aiReply = await generateAIReply(req.userId, conv.id);
      if (aiReply) {
        db.prepare(
          'INSERT INTO messages (conversation_id, sender, body) VALUES (?, ?, ?)'
        ).run(conv.id, 'ai', aiReply);
        sendToChannel(conv, aiReply).catch((e) => console.error('Channel send failed:', e.message));
      }
    } catch (e) {
      console.error('AI reply error:', e.message);
      const fallback = '[AI gagal merespons: ' + e.message + ']';
      db.prepare(
        'INSERT INTO messages (conversation_id, sender, body) VALUES (?, ?, ?)'
      ).run(conv.id, 'ai', fallback);
      aiReply = fallback;
    }
  }

  res.json({ ok: true, ai_reply: aiReply });
});

// Suggest an AI reply without saving — admin can edit before sending.
router.post('/:id/ai-suggest', async (req, res) => {
  const conv = db.prepare(
    'SELECT * FROM conversations WHERE id = ? AND user_id = ?'
  ).get(req.params.id, req.userId);
  if (!conv) return res.status(404).json({ error: 'Percakapan tidak ditemukan' });
  try {
    const reply = await generateAIReply(req.userId, conv.id);
    if (!reply) return res.json({ suggestion: '', note: 'Belum ada pesan pelanggan untuk dibalas.' });
    res.json({ suggestion: reply });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

router.patch('/:id', (req, res) => {
  const fields = [];
  const values = [];
  if ('ai_enabled' in (req.body || {})) {
    fields.push('ai_enabled = ?');
    values.push(req.body.ai_enabled ? 1 : 0);
  }
  if ('status' in (req.body || {})) {
    if (!['open', 'resolved'].includes(req.body.status)) {
      return res.status(400).json({ error: 'status harus "open" atau "resolved"' });
    }
    fields.push('status = ?');
    values.push(req.body.status);
  }
  if (fields.length === 0) return res.status(400).json({ error: 'Tidak ada field untuk diubah' });
  values.push(req.params.id, req.userId);
  const result = db.prepare(
    `UPDATE conversations SET ${fields.join(', ')} WHERE id = ? AND user_id = ?`
  ).run(...values);
  if (!result.changes) return res.status(404).json({ error: 'Percakapan tidak ditemukan' });
  res.json({ ok: true });
});

export default router;
