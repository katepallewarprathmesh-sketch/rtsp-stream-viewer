import { useCallback, useEffect, useState } from 'react';
import AddStreamForm from './components/AddStreamForm.jsx';
import StreamGrid from './components/StreamGrid.jsx';
import { apiUrl } from './config.js';

let nextId = 1;

export default function App() {
  const [streams, setStreams] = useState([]);
  const [demoStreams, setDemoStreams] = useState([]);

  useEffect(() => {
    fetch(apiUrl('/api/demo-streams/'))
      .then((r) => (r.ok ? r.json() : { streams: [] }))
      .then((data) => setDemoStreams(data.streams || []))
      .catch(() => {});
  }, []);

  const addStream = useCallback(
    (url) => {
      const trimmed = url.trim();
      if (!trimmed) return 'Please enter an RTSP URL.';
      if (!/^rtsps?:\/\//i.test(trimmed)) {
        return 'URL must start with rtsp:// or rtsps://';
      }
      if (streams.some((s) => s.url === trimmed)) {
        return 'That stream has already been added.';
      }
      setStreams((prev) => [...prev, { id: nextId++, url: trimmed }]);
      return null;
    },
    [streams]
  );

  const removeStream = useCallback((id) => {
    setStreams((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-icon">📹</span>
          <div>
            <h1>RTSP Stream Viewer</h1>
            <p className="tagline">
              Add RTSP camera URLs and watch them live, side by side.
            </p>
          </div>
        </div>
        <span className="stream-count">
          {streams.length} stream{streams.length === 1 ? '' : 's'}
        </span>
      </header>

      <AddStreamForm onAdd={addStream} demoStreams={demoStreams} />

      {streams.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🎥</div>
          <h2>No streams yet</h2>
          <p>
            Paste an RTSP URL above (e.g.{' '}
            <code>rtsp://user:pass@host:554/path</code>) and press{' '}
            <strong>Add Stream</strong>.
          </p>
        </div>
      ) : (
        <StreamGrid streams={streams} onRemove={removeStream} />
      )}

      <footer className="app-footer">
        Streams are transcoded server-side with FFmpeg and delivered over
        WebSockets (Django Channels).
      </footer>
    </div>
  );
}
