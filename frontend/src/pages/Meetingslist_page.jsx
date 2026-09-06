import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import "./Meetingslist_page.css";

export default function MeetingsListPage() {
  const [meetings, setMeetings] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    api    
      .listMeetings()
      .then((data) => {
        if (isMounted) setMeetings(data);
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
  }, []);

  if (isLoading) return <div className="meetings-status">Loading meetings...</div>;
  if (error) return <div className="meetings-status meetings-error">{error}</div>;

  return (
    <div className="meetings-page">
      <h1>Your meetings</h1>
      {meetings.length === 0 ? (
        <div className="meetings-empty">No meetings yet. Upload one to get started.</div>
      ) : (
        <ul className="meetings-list">
          {meetings.map((m) => (
            <li key={m.id} className="meeting-item">
              <Link to={`/meetings/${m.id}`}>
                <span className="meeting-title">{m.title || `Meeting ${m.id}`}</span>
                <span className={`meeting-status meeting-status-${m.status}`}>
                  {m.status}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}