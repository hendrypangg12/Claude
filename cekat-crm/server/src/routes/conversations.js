import { Router } from 'express';
import Anthropic from '@anthropic-ai/sdk';
import db from '../db.js';

const router = Router();

router.get('/', (req, res) => {
  const status = req.query.status; // 'open' | 'resolved' | undefined (all)
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

  let aiReply = null;
  if (sender === 'customer' && conv.ai_enabled && shouldAIRespond(req.userId)) {
    try {
      aiReply = await generateAIReply(req.userId, conv.id);
      if (aiReply) {
        db.prepare(
          'INSERT INTO messages (conversation_id, sender, body) VALUES (?, ?, ?)'
        ).run(conv.id, 'ai', aiReply);
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

function shouldAIRespond(userId) {
  const s = db.prepare('SELECT * FROM settings WHERE user_id = ?').get(userId);
  if (!s || !s.working_hours_enabled) return true;

  // Working hours enabled = AI only responds OUTSIDE work hours
  // (humans handle during work hours, like Cekat.AI's flow)
  const now = new Date();
  // Convert to Asia/Jakarta time (WIB, UTC+7) since target market is Indonesia
  const wibMs = now.getTime() + (now.getTimezoneOffset() + 7 * 60) * 60_000;
  const wib = new Date(wibMs);
  const day = wib.getDay(); // 0 = Sunday, 1 = Monday, etc.
  const hhmm = wib.toTimeString().slice(0, 5);

  const workDays = (s.work_days || '1,2,3,4,5').split(',').map((d) => parseInt(d, 10));
  const isWorkDay = workDays.includes(day);
  const inWorkHours = isWorkDay && hhmm >= s.work_start && hhmm < s.work_end;

  return !inWorkHours; // AI replies only when humans aren't on shift
}

async function generateAIReply(userId, conversationId) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return '[AI belum aktif — admin perlu mengisi ANTHROPIC_API_KEY di server/.env]';
  }

  const knowledge = db.prepare('SELECT content FROM knowledge WHERE user_id = ?').get(userId);
  const recentMessages = db.prepare(`
    SELECT sender, body FROM messages
    WHERE conversation_id = ?
    ORDER BY id DESC LIMIT 20
  `).all(conversationId).reverse();

  const systemBlocks = [
    {
      type: 'text',
      text: [
        'Kamu adalah AI customer service untuk bisnis ini.',
        'Jawab dengan ramah, singkat, dan menggunakan Bahasa Indonesia yang natural.',
        'Jika tidak tahu jawabannya, akui jujur dan tawarkan untuk diteruskan ke admin manusia.',
        'Jangan mengarang harga, jadwal, atau kebijakan yang tidak ada di knowledge base.',
        '',
        'KNOWLEDGE BASE / SOP BISNIS:',
        knowledge?.content?.trim() || '(Belum ada knowledge base. Beritahu pelanggan bahwa admin akan segera membantu.)',
      ].join('\n'),
      cache_control: { type: 'ephemeral' },
    },
  ];

  const formatted = recentMessages.map((m) => ({
    role: m.sender === 'customer' ? 'user' : 'assistant',
    content: m.body,
  }));

  if (formatted.length === 0 || formatted[0].role !== 'user') {
    return null;
  }

  const client = new Anthropic();
  const response = await client.messages.create({
    model: 'claude-haiku-4-5',
    max_tokens: 512,
    system: systemBlocks,
    messages: formatted,
  });

  const textBlock = response.content.find((b) => b.type === 'text');
  return textBlock?.text || null;
}

export default router;
