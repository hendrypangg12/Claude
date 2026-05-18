import { useEffect, useState, useRef } from 'react';
import { api } from '../api.js';

export default function Inbox() {
  const [conversations, setConversations] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draftCustomer, setDraftCustomer] = useState('');
  const [draftAgent, setDraftAgent] = useState('');
  const [sending, setSending] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [statusFilter, setStatusFilter] = useState('open'); // 'open' | 'resolved' | 'all'
  const bottomRef = useRef(null);

  const active = conversations.find((c) => c.id === activeId);

  async function loadConversations() {
    const query = statusFilter === 'all' ? '' : `?status=${statusFilter}`;
    const list = await api('/conversations' + query);
    setConversations(list);
    if (list.length && !list.find((c) => c.id === activeId)) {
      setActiveId(list[0].id);
    } else if (!list.length) {
      setActiveId(null);
    }
  }

  async function loadMessages(id) {
    const list = await api(`/conversations/${id}/messages`);
    setMessages(list);
  }

  const [templates, setTemplates] = useState([]);
  const [suggesting, setSuggesting] = useState(false);

  useEffect(() => {
    api('/contacts').then(setContacts);
    api('/quick-replies').then(setTemplates);
  }, []);

  useEffect(() => {
    loadConversations();
  }, [statusFilter]);

  useEffect(() => {
    if (activeId) loadMessages(activeId);
  }, [activeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function send(sender, body, setter) {
    if (!body.trim() || !activeId) return;
    setSending(true);
    try {
      await api(`/conversations/${activeId}/messages`, {
        method: 'POST',
        body: { sender, body: body.trim() },
      });
      setter('');
      await loadMessages(activeId);
      await loadConversations();
    } catch (err) {
      alert(err.message);
    } finally {
      setSending(false);
    }
  }

  async function toggleAI(enabled) {
    await api(`/conversations/${activeId}`, {
      method: 'PATCH',
      body: { ai_enabled: enabled },
    });
    await loadConversations();
  }

  async function updateStatus(newStatus) {
    await api(`/conversations/${activeId}`, {
      method: 'PATCH',
      body: { status: newStatus },
    });
    await loadConversations();
  }

  async function getAISuggestion() {
    if (!activeId) return;
    setSuggesting(true);
    try {
      const { suggestion, note } = await api(`/conversations/${activeId}/ai-suggest`, { method: 'POST' });
      if (suggestion) setDraftAgent(suggestion);
      else if (note) alert(note);
    } catch (err) {
      alert('Gagal minta saran AI: ' + err.message);
    } finally {
      setSuggesting(false);
    }
  }

  async function startConversation(contactId) {
    const { id } = await api('/conversations', { method: 'POST', body: { contact_id: contactId } });
    setShowNew(false);
    await loadConversations();
    setActiveId(id);
  }

  return (
    <>
      <div className="inbox-grid">
        <div className="inbox-panel">
          <div className="panel-header">
            <span>Percakapan</span>
            <button onClick={() => setShowNew(true)} className="primary" style={{ padding: '5px 10px', fontSize: 12 }}>
              + Baru
            </button>
          </div>
          <div className="filter-tabs">
            {[
              { v: 'open', l: 'Aktif' },
              { v: 'resolved', l: 'Selesai' },
              { v: 'all', l: 'Semua' },
            ].map((t) => (
              <button
                key={t.v}
                className={'filter-tab' + (statusFilter === t.v ? ' active' : '')}
                onClick={() => setStatusFilter(t.v)}
              >
                {t.l}
              </button>
            ))}
          </div>
          <div className="panel-body">
            {conversations.length === 0 ? (
              <div className="empty-state">
                <div className="big">💬</div>
                <div>Belum ada percakapan.</div>
                <div style={{ fontSize: 12, marginTop: 8 }}>Tambah kontak dulu di menu Kontak.</div>
              </div>
            ) : (
              conversations.map((c) => (
                <div
                  key={c.id}
                  className={'conv-row' + (c.id === activeId ? ' active' : '')}
                  onClick={() => setActiveId(c.id)}
                >
                  <div className="name">
                    {c.contact_name}
                    {c.contact_tag && <span className="tag">{c.contact_tag}</span>}
                    {c.ai_enabled ? <span className="tag" style={{ background: '#ecfdf5', color: '#16a34a' }}>AI</span> : null}
                  </div>
                  <div className="preview">
                    {c.last_sender ? `${labelSender(c.last_sender)}: ${c.last_message || ''}` : 'Belum ada pesan'}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="inbox-panel">
          {active ? (
            <>
              <div className="panel-header">
                <span>
                  {active.contact_name}
                  {active.contact_phone && <small style={{ color: 'var(--muted)', fontWeight: 400 }}>· {active.contact_phone}</small>}
                  {active.status === 'resolved' && <span className="tag" style={{ background: '#ecfdf5', color: 'var(--success)', marginLeft: 8 }}>Selesai</span>}
                </span>
                {active.status === 'resolved' ? (
                  <button onClick={() => updateStatus('open')} style={{ padding: '5px 10px', fontSize: 12 }}>
                    Buka Kembali
                  </button>
                ) : (
                  <button onClick={() => updateStatus('resolved')} style={{ padding: '5px 10px', fontSize: 12, borderColor: 'var(--success)', color: 'var(--success)' }}>
                    ✓ Tandai Selesai
                  </button>
                )}
              </div>
              <div className="toggle-row">
                <input
                  type="checkbox"
                  id="ai-toggle"
                  checked={!!active.ai_enabled}
                  onChange={(e) => toggleAI(e.target.checked)}
                />
                <label htmlFor="ai-toggle" style={{ margin: 0 }}>AI Agent aktif (otomatis balas pesan pelanggan)</label>
              </div>
              <div className="panel-body chat-messages">
                {messages.length === 0 ? (
                  <div className="empty-state">Belum ada pesan. Gunakan panel kanan untuk simulasi.</div>
                ) : (
                  messages.map((m) => (
                    <div key={m.id} className={'msg ' + m.sender}>
                      {m.sender === 'ai' && <div className="ai-badge">AI</div>}
                      <div>{m.body}</div>
                      <div className="meta">{labelSender(m.sender)} · {formatTime(m.created_at)}</div>
                    </div>
                  ))
                )}
                <div ref={bottomRef} />
              </div>
              <div className="panel-footer">
                {(templates.length > 0 || true) && (
                  <div className="quick-reply-row">
                    <button
                      className="quick-reply-btn ai-suggest"
                      onClick={getAISuggestion}
                      disabled={suggesting}
                      title="AI menulis saran balasan berdasarkan riwayat chat"
                    >
                      {suggesting ? '...' : '🤖 Saran AI'}
                    </button>
                    {templates.map((t) => (
                      <button
                        key={t.id}
                        className="quick-reply-btn"
                        onClick={() => setDraftAgent((cur) => cur ? cur + '\n' + t.body : t.body)}
                        title={t.body}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                )}
                <div className="chat-input-row">
                  <textarea
                    value={draftAgent}
                    onChange={(e) => setDraftAgent(e.target.value)}
                    placeholder="Ketik balasan admin..."
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        send('agent', draftAgent, setDraftAgent);
                      }
                    }}
                  />
                  <button
                    className="primary"
                    disabled={sending || !draftAgent.trim()}
                    onClick={() => send('agent', draftAgent, setDraftAgent)}
                  >
                    Kirim
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <div className="big">💬</div>
              <div>Pilih percakapan di kiri</div>
            </div>
          )}
        </div>

        <div className="inbox-panel">
          <div className="panel-header">Simulasi Pelanggan</div>
          <div className="panel-body" style={{ padding: 16 }}>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 0 }}>
              Karena belum ada integrasi WhatsApp/Instagram, ketik di sini untuk simulasi pesan dari pelanggan.
              Jika AI aktif, balasan otomatis akan muncul.
            </p>
            {active ? (
              <>
                <textarea
                  value={draftCustomer}
                  onChange={(e) => setDraftCustomer(e.target.value)}
                  placeholder={`Pesan sebagai ${active.contact_name}...`}
                  rows={4}
                />
                <button
                  className="primary"
                  style={{ width: '100%', marginTop: 8 }}
                  disabled={sending || !draftCustomer.trim()}
                  onClick={() => send('customer', draftCustomer, setDraftCustomer)}
                >
                  {sending ? 'Mengirim...' : 'Kirim Pesan Pelanggan'}
                </button>
              </>
            ) : (
              <div style={{ color: 'var(--muted)', fontSize: 13 }}>Pilih percakapan dulu.</div>
            )}
          </div>
        </div>
      </div>

      {showNew && (
        <div className="modal-backdrop" onClick={() => setShowNew(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Mulai Percakapan Baru</h3>
            {contacts.length === 0 ? (
              <p>Belum ada kontak. Tambah kontak dulu di menu Kontak.</p>
            ) : (
              <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                {contacts.map((c) => (
                  <div
                    key={c.id}
                    className="conv-row"
                    style={{ borderRadius: 8 }}
                    onClick={() => startConversation(c.id)}
                  >
                    <div className="name">{c.name}</div>
                    <div className="preview">{c.phone || c.email || '-'}</div>
                  </div>
                ))}
              </div>
            )}
            <div className="modal-actions">
              <button onClick={() => setShowNew(false)}>Tutup</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function labelSender(s) {
  return s === 'customer' ? 'Pelanggan' : s === 'agent' ? 'Admin' : 'AI';
}

function formatTime(iso) {
  try {
    const d = new Date(iso + 'Z');
    return d.toLocaleString('id-ID', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' });
  } catch {
    return iso;
  }
}
