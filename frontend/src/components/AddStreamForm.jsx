import { useState } from 'react';

export default function AddStreamForm({ onAdd, demoStreams }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState(null);

  const submit = (e) => {
    e.preventDefault();
    const err = onAdd(url);
    setError(err);
    if (!err) setUrl('');
  };

  const addDemo = (demoUrl) => {
    const err = onAdd(demoUrl);
    setError(err);
  };

  return (
    <section className="add-form-wrap">
      <form className="add-form" onSubmit={submit}>
        <input
          type="text"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (error) setError(null);
          }}
          placeholder="rtsp://username:password@host:554/path"
          aria-label="RTSP stream URL"
          spellCheck="false"
        />
        <button type="submit" className="btn btn-primary">
          + Add Stream
        </button>
      </form>
      {error && <div className="form-error">⚠ {error}</div>}
      {demoStreams.length > 0 && (
        <div className="demo-row">
          <span className="demo-label">Try a demo stream:</span>
          {demoStreams.map((d, i) => (
            <button
              key={d}
              type="button"
              className="btn btn-ghost btn-small"
              onClick={() => addDemo(d)}
              title={d}
            >
              Demo camera {i + 1}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
