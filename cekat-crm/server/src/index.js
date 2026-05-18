import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { requireAuth } from './middleware/auth.js';
import authRoutes from './routes/auth.js';
import contactsRoutes from './routes/contacts.js';
import conversationsRoutes from './routes/conversations.js';
import knowledgeRoutes from './routes/knowledge.js';
import './db.js';

const app = express();
app.use(cors({ origin: process.env.CLIENT_ORIGIN || 'http://localhost:5173' }));
app.use(express.json({ limit: '1mb' }));

app.get('/api/health', (_req, res) => res.json({ ok: true }));
app.use('/api/auth', authRoutes);
app.use('/api/contacts', requireAuth, contactsRoutes);
app.use('/api/conversations', requireAuth, conversationsRoutes);
app.use('/api/knowledge', requireAuth, knowledgeRoutes);

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

const port = process.env.PORT || 3001;
app.listen(port, () => {
  console.log(`Cekat CRM server listening on http://localhost:${port}`);
});
