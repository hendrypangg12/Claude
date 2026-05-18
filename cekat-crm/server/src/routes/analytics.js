import { Router } from 'express';
import db from '../db.js';

const router = Router();

router.get('/', (req, res) => {
  const userId = req.userId;

  // Totals
  const totalContacts = db.prepare('SELECT COUNT(*) AS c FROM contacts WHERE user_id = ?').get(userId).c;
  const convStats = db.prepare(`
    SELECT
      COUNT(*) AS total,
      SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_count,
      SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) AS resolved_count,
      SUM(CASE WHEN ai_enabled = 1 THEN 1 ELSE 0 END) AS ai_active
    FROM conversations WHERE user_id = ?
  `).get(userId);

  const msgStats = db.prepare(`
    SELECT
      COUNT(*) AS total,
      SUM(CASE WHEN sender = 'customer' THEN 1 ELSE 0 END) AS customer_count,
      SUM(CASE WHEN sender = 'agent' THEN 1 ELSE 0 END) AS agent_count,
      SUM(CASE WHEN sender = 'ai' THEN 1 ELSE 0 END) AS ai_count
    FROM messages m
    JOIN conversations c ON c.id = m.conversation_id
    WHERE c.user_id = ?
  `).get(userId);

  // Messages per day for last 14 days
  const dailyMessages = db.prepare(`
    SELECT
      DATE(m.created_at) AS day,
      SUM(CASE WHEN m.sender = 'customer' THEN 1 ELSE 0 END) AS customer,
      SUM(CASE WHEN m.sender = 'agent' THEN 1 ELSE 0 END) AS agent,
      SUM(CASE WHEN m.sender = 'ai' THEN 1 ELSE 0 END) AS ai
    FROM messages m
    JOIN conversations c ON c.id = m.conversation_id
    WHERE c.user_id = ? AND m.created_at >= datetime('now', '-14 days')
    GROUP BY DATE(m.created_at)
    ORDER BY day ASC
  `).all(userId);

  // Top 5 contacts by message count
  const topContacts = db.prepare(`
    SELECT ct.id, ct.name, ct.tag, ct.phone, COUNT(m.id) AS message_count
    FROM contacts ct
    JOIN conversations c ON c.contact_id = ct.id
    JOIN messages m ON m.conversation_id = c.id
    WHERE ct.user_id = ?
    GROUP BY ct.id
    ORDER BY message_count DESC
    LIMIT 5
  `).all(userId);

  // AI vs human handled rate
  const aiShare = msgStats.total > 0
    ? Math.round((msgStats.ai_count / (msgStats.ai_count + msgStats.agent_count || 1)) * 100)
    : 0;

  res.json({
    totals: {
      contacts: totalContacts,
      conversations: convStats.total || 0,
      open: convStats.open_count || 0,
      resolved: convStats.resolved_count || 0,
      ai_active: convStats.ai_active || 0,
      messages: msgStats.total || 0,
      messages_customer: msgStats.customer_count || 0,
      messages_agent: msgStats.agent_count || 0,
      messages_ai: msgStats.ai_count || 0,
      ai_share_percent: aiShare,
    },
    daily_messages: dailyMessages,
    top_contacts: topContacts,
  });
});

export default router;
