const TOKEN_KEY = 'cekat_token';
const USER_KEY = 'cekat_user';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function setSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function api(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch('/api' + path, {
    ...options,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) {
    let msg = 'Request gagal';
    try {
      const data = await res.json();
      msg = data.error || msg;
    } catch {}
    if (res.status === 401) {
      clearSession();
      window.location.href = '/login';
    }
    throw new Error(msg);
  }

  if (res.status === 204) return null;
  return res.json();
}
