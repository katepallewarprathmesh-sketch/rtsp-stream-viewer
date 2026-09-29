import StreamPlayer from './StreamPlayer.jsx';

export default function StreamGrid({ streams, onRemove }) {
  return (
    <div className={`stream-grid cols-${Math.min(streams.length, 3)}`}>
      {streams.map((stream) => (
        <StreamPlayer
          key={stream.id}
          url={stream.url}
          onRemove={() => onRemove(stream.id)}
        />
      ))}
    </div>
  );
}
