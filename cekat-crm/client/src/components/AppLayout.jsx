import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { clearSession, getUser } from '../api.js';

export default function AppLayout() {
  const user = getUser();
  const navigate = useNavigate();

  function logout() {
    clearSession();
    navigate('/login');
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">BerBisnis</div>
        <NavLink to="/inbox" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
          💬 Inbox
        </NavLink>
        <NavLink to="/contacts" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
          👥 Kontak
        </NavLink>
        <NavLink to="/knowledge" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
          📚 Knowledge Base
        </NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
          📊 Dashboard
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
          ⚙️ Pengaturan
        </NavLink>
        <div className="user-box">
          <div className="uname">{user?.name}</div>
          <div className="uemail">{user?.email}</div>
          <button onClick={logout} style={{ width: '100%' }}>Keluar</button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
