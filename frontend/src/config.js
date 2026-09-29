/**
 * Backend endpoints.
 *
 * By default the app is same-origin: Django serves the built frontend and
 * the WebSocket, so relative URLs work everywhere (local dev via the Vite
 * proxy, and single-server deployments).
 *
 * For split hosting (e.g. frontend on GitHub Pages + backend on Render),
 * set VITE_BACKEND_URL at build time:
 *   VITE_BACKEND_URL=https://my-backend.onrender.com npm run build
 */
const raw = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/+$/, '');

export function apiUrl(path) {
  return raw ? `${raw}${path}` : path;
}

export function wsUrl(path) {
  if (raw) {
    return raw.replace(/^http/, 'ws') + path;
  }
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}${path}`;
}
