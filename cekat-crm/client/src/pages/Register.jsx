import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, setSession } from '../api.js';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { token, user } = await api('/auth/register', {
        method: 'POST',
        body: { name, email, password },
      });
      setSession(token, user);
      navigate('/inbox');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Daftar Akun</h1>
        <div className="subtitle">Buat akun bisnis Anda</div>
        {error && <div className="error-banner">{error}</div>}
        <div className="form-row">
          <label>Nama Bisnis / Tim</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="form-row">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="form-row">
          <label>Password (min 6 karakter)</label>
          <input type="password" minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <div className="actions">
          <button type="submit" className="primary" disabled={loading}>
            {loading ? 'Memuat...' : 'Daftar'}
          </button>
        </div>
        <div className="footer-link">
          Sudah punya akun? <Link to="/login">Masuk</Link>
        </div>
      </form>
    </div>
  );
}
