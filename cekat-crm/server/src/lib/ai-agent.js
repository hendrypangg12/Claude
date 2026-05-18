import Anthropic from '@anthropic-ai/sdk';
import db from '../db.js';

export function shouldAIRespond(userId) {
  const s = db.prepare('SELECT * FROM settings WHERE user_id = ?').get(userId);
  if (!s || !s.working_hours_enabled) return true;

  // Working hours enabled = AI only responds OUTSIDE work hours
  // (humans handle during work hours, like Cekat.AI's flow)
  const now = new Date();
  // Convert to Asia/Jakarta time (WIB, UTC+7)
  const wibMs = now.getTime() + (now.getTimezoneOffset() + 7 * 60) * 60_000;
  const wib = new Date(wibMs);
  const day = wib.getDay();
  const hhmm = wib.toTimeString().slice(0, 5);

  const workDays = (s.work_days || '1,2,3,4,5').split(',').map((d) => parseInt(d, 10));
  const isWorkDay = workDays.includes(day);
  const inWorkHours = isWorkDay && hhmm >= s.work_start && hhmm < s.work_end;

  return !inWorkHours;
}

export async function generateAIReply(userId, conversationId) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return '[AI belum aktif — admin perlu mengisi ANTHROPIC_API_KEY di server/.env]';
  }

  const knowledge = db.prepare('SELECT content FROM knowledge WHERE user_id = ?').get(userId);
  const settings = db.prepare('SELECT business_name, ai_tone FROM settings WHERE user_id = ?').get(userId);
  const recentMessages = db.prepare(`
    SELECT sender, body FROM messages
    WHERE conversation_id = ?
    ORDER BY id DESC LIMIT 20
  `).all(conversationId).reverse();

  const toneInstruction = {
    friendly: 'Pakai gaya bahasa ramah dan santai, sapaan "kak". Boleh pakai emoji sesekali.',
    formal: 'Pakai gaya bahasa formal dan profesional, sapaan "Bapak/Ibu". Hindari singkatan dan emoji.',
    playful: 'Pakai gaya bahasa santai, hangat, dengan sedikit humor. Pakai emoji untuk membuat suasana enak.',
    concise: 'Jawab sangat singkat dan to the point. Maksimal 2 kalimat per balasan kecuali harus menjelaskan detail.',
  }[settings?.ai_tone || 'friendly'];

  const systemBlocks = [
    {
      type: 'text',
      text: [
        `Kamu adalah AI customer service untuk ${settings?.business_name || 'bisnis ini'}.`,
        'Jawab menggunakan Bahasa Indonesia yang natural.',
        toneInstruction,
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

  if (formatted.length === 0 || formatted[formatted.length - 1].role !== 'user') {
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
