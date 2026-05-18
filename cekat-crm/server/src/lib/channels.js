// Channel send dispatcher. Currently routes WhatsApp messages back via Twilio.
// Falls back to no-op for the 'simulator' channel.
import twilio from 'twilio';

let twilioClient = null;
function getTwilio() {
  if (twilioClient) return twilioClient;
  const sid = process.env.TWILIO_ACCOUNT_SID;
  const token = process.env.TWILIO_AUTH_TOKEN;
  if (!sid || !token) return null;
  twilioClient = twilio(sid, token);
  return twilioClient;
}

export function isTwilioConfigured() {
  return !!(
    process.env.TWILIO_ACCOUNT_SID &&
    process.env.TWILIO_AUTH_TOKEN &&
    process.env.TWILIO_WHATSAPP_FROM
  );
}

export async function sendToChannel(conversation, body) {
  if (conversation.channel !== 'whatsapp') return;
  const client = getTwilio();
  if (!client) {
    console.warn('[channels] Twilio not configured — skipping WhatsApp send');
    return;
  }
  // Look up contact phone
  // Imported lazily to avoid circular deps in test scenarios
  const db = (await import('../db.js')).default;
  const contact = db.prepare('SELECT phone FROM contacts WHERE id = ?').get(conversation.contact_id);
  if (!contact?.phone) {
    console.warn('[channels] Contact has no phone — cannot send WhatsApp');
    return;
  }
  const to = contact.phone.startsWith('whatsapp:')
    ? contact.phone
    : `whatsapp:+${contact.phone.replace(/^\+/, '')}`;
  await client.messages.create({
    from: process.env.TWILIO_WHATSAPP_FROM,
    to,
    body,
  });
}
