import { useCallback, useEffect, useRef, useState } from 'react';
import { wsUrl } from '../config.js';

const WS_PATH = '/ws/stream/';

/**
 * One tile in the grid. Owns its own WebSocket connection; the backend
 * spawns a dedicated FFmpeg process per connection, so every player is
 * fully independent (pausing/removing one never affects the others).
 */
export default function StreamPlayer({ url, onRemove }) {
  const imgRef = useRef(null);
  const wsRef = useRef(null);
  const blobUrlRef = useRef(null);
  const frameCounter = useRef(0);
  const [state, setState] = useState('connecting'); // connecting|live|paused|error|closed
  const [error, setError] = useState(null);
  const [fps, setFps] = useState(0);
  const [hasFrame, setHasFrame] = useState(false);

  const connect = useCallback(() => {
    setState('connecting');
    setError(null);
    frameCounter.current = 0;

    const ws = new WebSocket(wsUrl(WS_PATH));
    ws.binaryType = 'blob';
    wsRef.current = ws;

    ws.onopen = () => ws.send(JSON.stringify({ action: 'play', url }));

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'status') {
            setState(msg.state);
            if (msg.state === 'live') setError(null);
          } else if (msg.type === 'error') {
            setState('error');
            setError(msg.message);
          }
        } catch {
          /* ignore malformed messages */
        }
        return;
      }
      // Binary frame: a JPEG image.
      frameCounter.current += 1;
      const objectUrl = URL.createObjectURL(event.data);
      if (imgRef.current) {
        imgRef.current.src = objectUrl;
        setHasFrame(true);
      }
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = objectUrl;
    };

    ws.onclose = () => {
      setState((prev) => (prev === 'error' ? prev : 'closed'));
    };
    ws.onerror = () => {
      setState('error');
      setError((prev) => prev || 'WebSocket connection failed.');
    };
  }, [url]);

  useEffect(() => {
    connect();
    const fpsTimer = setInterval(() => {
      setFps(frameCounter.current);
      frameCounter.current = 0;
    }, 1000);
    return () => {
      clearInterval(fpsTimer);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, [connect]);

  const togglePlayPause = () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (state === 'live' || state === 'connecting') {
      ws.send(JSON.stringify({ action: 'pause' }));
    } else if (state === 'paused') {
      ws.send(JSON.stringify({ action: 'play', url }));
    }
  };

  const retry = () => {
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }
    setHasFrame(false);
    connect();
  };

  const badge = {
    connecting: { text: 'CONNECTING', cls: 'badge-connecting' },
    live: { text: '● LIVE', cls: 'badge-live' },
    paused: { text: '❚❚ PAUSED', cls: 'badge-paused' },
    error: { text: '✕ ERROR', cls: 'badge-error' },
    closed: { text: 'DISCONNECTED', cls: 'badge-error' },
    stopped: { text: 'STOPPED', cls: 'badge-paused' },
  }[state] || { text: state.toUpperCase(), cls: '' };

  const canToggle = state === 'live' || state === 'paused';

  return (
    <div className="stream-card">
      <div className="stream-view">
        <img
          ref={imgRef}
          alt="Live stream"
          className="stream-img"
          style={{ display: hasFrame ? 'block' : 'none' }}
          draggable={false}
        />
        {!hasFrame && state === 'connecting' && (
          <div className="stream-overlay">
            <div className="spinner" />
            <span>Connecting to stream…</span>
          </div>
        )}
        {state === 'error' && (
          <div className="stream-overlay overlay-error">
            <span className="overlay-icon">⚠️</span>
            <p className="overlay-message">{error || 'Stream failed.'}</p>
            <button className="btn btn-primary btn-small" onClick={retry}>
              ↻ Retry
            </button>
          </div>
        )}
        {state === 'closed' && (
          <div className="stream-overlay overlay-error">
            <p className="overlay-message">Connection closed.</p>
            <button className="btn btn-primary btn-small" onClick={retry}>
              ↻ Reconnect
            </button>
          </div>
        )}
        {state === 'paused' && hasFrame && (
          <div className="stream-overlay overlay-paused">
            <span className="overlay-icon">❚❚</span>
          </div>
        )}
        <span className={`badge ${badge.cls}`}>{badge.text}</span>
        {state === 'live' && <span className="fps">{fps} fps</span>}
      </div>
      <div className="stream-toolbar">
        <span className="stream-url" title={url}>
          {url}
        </span>
        <div className="stream-buttons">
          <button
            className="btn btn-icon"
            onClick={togglePlayPause}
            disabled={!canToggle}
            title={state === 'paused' ? 'Play' : 'Pause'}
          >
            {state === 'paused' ? '▶' : '❚❚'}
          </button>
          <button
            className="btn btn-icon btn-danger"
            onClick={onRemove}
            title="Remove stream"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}
