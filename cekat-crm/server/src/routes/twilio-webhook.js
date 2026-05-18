// Twilio WhatsApp inbound webhook.
//
// SETUP (di laptop user):
// 1. Buat akun Twilio gratis, aktifkan WhatsApp Sandbox di
//    https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
// 2. Set webhook "WHEN A MESSAGE COMES IN" ke:
//    https://<ngrok-url>/api/webhooks/twilio/whatsapp  (POST)
// 3. Set env vars:
//    TWILIO_ACCOUNT_SID=AC...
//    TWILIO_AUTH_TOKEN=...
//    TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   (nomor sandbox Twilio)
//    TWILIO_DEFAULT_USER_ID=1                    (user yang "memiliki" inbox sandbox)
// 4. Untuk expose server local: `npx ngrok http 3001`
//
// Single-tenant assumption: semua pesan masuk diarahkan ke TWILIO_DEFAULT_USER_ID.
// Multi-tenant butuh routing by To-number → user mapping, di luar scope MVP.

import { Router } from 'express';
import twilio from 'twilio';
import db from '../db.js';
import { shouldAIRespond, generateAIReply } from '../lib/ai-agent.js';
import { sendToChannel } from '../lib/channels.js';

const router = Router();

function verifyTwilio(req) {
  if (process.env.TWILIO_SKIP_VERIFY === 'true') return true;
  const sig = req.headers['x-twilio-signature'];
  const token = process.env.TWILIO_AUTH_TOKEN;
  if (!sig || !token) return false;
  const url = (process.env.TWILIO_WEBHOOK_URL || '') + req.originalUrl;
  return twilio.validateRequest(token, sig, url, req.body);
}

router.post('/whatsapp', async (req, res) => {
  if (!verifyTwilio(req)) {
    console.warn('[twilio] Webhook signature mismatch. Set TWILIO_WEBHOOK_URL atau TWILIO_SKIP_VERIFY=true untuk dev.');
    // Tetap respon OK biar Twilio tidak retry, tapi tidak proses.
    return res.type('text/xml').send('<Response></Response>');
  }

  const from = req.body.From || ''; // "whatsapp:+628123..."
  const body = (req.body.Body || '').trim();
  if (!from || !body) {
    return res.type('text/xml').send('<Response></Response>');
  }

  const phone = from.replace('whatsapp:', '').replace(/^\+/, '');
  const userId = parseInt(process.env.TWILIO_DEFAULT_USER_ID || '1', 10);

  // Find or create contact
  let contact = db.prepare(
    'SELECT * FROM contacts WHERE user_id = ? AND phone = ?'
  ).get(userId, phone);
  if (!contact) {
    const info = db.prepare(
      'INSERT INTO contacts (user_id, name, phone) VALUES (?, ?, ?)'
    ).run(userId, `WhatsApp ${phone.slice(-4)}`, phone);
    contact = { id: info.lastInsertRowid, user_id: userId, phone };
  }

  // Find or create conversation (whatsapp channel)
  let conv = db.prepare(
    "SELECT * FROM conversations WHERE user_id = ? AND contact_id = ? AND channel = 'whatsapp'"
  ).get(userId, contact.id);
  if (!conv) {
    const info = db.prepare(
      "INSERT INTO conversations (user_id, contact_id, channel) VALUES (?, ?, 'whatsapp')"
    ).run(userId, contact.id);
    conv = { id: info.lastInsertRowid, user_id: userId, contact_id: contact.id, channel: 'whatsapp', ai_enabled: 1, status: 'open' };

    // Auto-greeting on first contact
    const settings = db.prepare('SELECT greeting FROM settings WHERE user_id = ?').get(userId);
    if (settings?.greeting?.trim()) {
      db.prepare(
        'INSERT INTO messages (conversation_id, sender, body) VALUES (?, ?, ?)'
      ).run(conv.id, 'ai', settings.greeting.trim());
      sendToChannel(conv, settings.greeting.trim()).catch((e) => console.error(e));
    }
  }

  // Save inbound message
  db.prepare(
    'INSERT INTO messages (conversation_id, sender, body) VALUES (?, ?, ?)'
  ).run(conv.id, 'customer', body);
  db.prepare("UPDATE conversations SET updated_at = datetime('now') WHERE id = ?").run(conv.id);

  // AI reply if appropriate
  if (conv.ai_enabled && shouldAIRespond(userId)) {
    try {
      const reply = await generateAIReply(userId, conv.id);
      if (reply) {
        db.prepare(
          'INSERT INTO messages (conversation_id, sender, body) VALUES (?, ?, ?)'
        ).run(conv.id, 'ai', reply);
        // Reply via TwiML (faster than separate Twilio API call)
        const twiml = new twilio.twiml.MessagingResponse();
        twiml.message(reply);
        return res.type('text/xml').send(twiml.toString());
      }
    } catch (e) {
      console.error('[twilio] AI reply error:', e.message);
    }
  }

  res.type('text/xml').send('<Response></Response>');
});

export default router;
