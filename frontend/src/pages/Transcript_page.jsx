import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api.js";
import "./Transcript_page.css";

export default function TranscriptPage() {
  const { id } = useParams();
  const [transcript, setTranscript] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    api
      .getTranscript(id)
      .then((data) => {
        if (isMounted) setTranscript(data);
      })
      .catch((err) => {
        if (isMounted) setError(err.message);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [id]);

  if (isLoading) return <div className="transcript-status">Loading transcript...</div>;
  if (error) return <div className="transcript-status transcript-error">{error}</div>;
  if (!transcript) return <div className="transcript-status">No transcript found.</div>;

  return (
    <div className="transcript-page">
      <div className="transcript-header">
        <h1>{transcript.title || `Meeting ${id}`}</h1>
        <Link to={`/meetings/${id}/chat`} className="transcript-chat-link">
          Chat with this meeting →
        </Link>
      </div>

      <div className="transcript-body">
        {transcript.segments?.length ? (
          transcript.segments.map((seg, idx) => (
            <div key={idx} className="transcript-segment">
              <div className="transcript-meta">
                {seg.speaker && <span className="transcript-speaker">{seg.speaker}</span>}
                {seg.start != null && (
                  <span className="transcript-time">{formatTime(seg.start)}</span>
                )}
              </div>
              <p className="transcript-text">{seg.text}</p>
            </div>
          ))
        ) : (
          <div className="transcript-empty">No segments available yet.</div>
        )}
      </div>
    </div>
  );
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}