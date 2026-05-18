import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, setSession } from '../api.js';

export default function Login() {
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
      const { token, user } = await api('/auth/login', {
        method: 'POST',
        body: { email, password },
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
        <h1>Cekat CRM</h1>
        <div className="subtitle">Masuk ke akun Anda</div>
        {error && <div className="error-banner">{error}</div>}
        <div className="form-row">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="form-row">
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <div className="actions">
          <button type="submit" className="primary" disabled={loading}>
            {loading ? 'Memuat...' : 'Masuk'}
          </button>
        </div>
        <div className="footer-link">
          Belum punya akun? <Link to="/register">Daftar</Link>
        </div>
      </form>
    </div>
  );
}
