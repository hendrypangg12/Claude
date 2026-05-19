import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { requireAuth } from './middleware/auth.js';
import authRoutes from './routes/auth.js';
import contactsRoutes from './routes/contacts.js';
import conversationsRoutes from './routes/conversations.js';
import knowledgeRoutes from './routes/knowledge.js';
import settingsRoutes from './routes/settings.js';
import quickRepliesRoutes from './routes/quick-replies.js';
import analyticsRoutes from './routes/analytics.js';
import twilioWebhookRoutes from './routes/twilio-webhook.js';
import './db.js';

const app = express();
app.use(cors({ origin: process.env.CLIENT_ORIGIN || 'http://localhost:5173' }));

// Twilio webhooks send application/x-www-form-urlencoded
app.use('/api/webhooks/twilio', express.urlencoded({ extended: false }), twilioWebhookRoutes);

// All other routes use JSON
app.use(express.json({ limit: '2mb' }));

app.get('/api/health', (_req, res) => res.json({ ok: true }));
app.use('/api/auth', authRoutes);
app.use('/api/contacts', requireAuth, contactsRoutes);
app.use('/api/conversations', requireAuth, conversationsRoutes);
app.use('/api/knowledge', requireAuth, knowledgeRoutes);
app.use('/api/settings', requireAuth, settingsRoutes);
app.use('/api/quick-replies', requireAuth, quickRepliesRoutes);
app.use('/api/analytics', requireAuth, analyticsRoutes);

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

const port = process.env.PORT || 3001;
app.listen(port, () => {
  console.log(`BerBisnis server listening on http://localhost:${port}`);
});
