import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import "./Chat_page.css";

export default function ChatPage() {
  const { id } = useParams();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    let isMounted = true;
    api
      .getChatHistory(id)
      .then((data) => {
        if (isMounted) setMessages(data);
      })
      .catch((err) => {
        if (isMounted) setError(err.message);
      })
      .finally(() => {
        if (isMounted) setIsLoadingHistory(false);
      });
    return () => {
      isMounted = false;
    };
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    const userMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsSending(true);
    setError(null);

    try {
      const reply = await api.sendChatMessage(id, text);
      setMessages((prev) => [...prev, reply]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="chat-page">
      <h1>Chat</h1>

      <div className="chat-window">
        {isLoadingHistory ? (
          <div className="chat-status">Loading conversation...</div>
        ) : messages.length === 0 ? (
          <div className="chat-empty">Ask something about this meeting.</div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`chat-bubble chat-bubble-${msg.role}`}>
              <p>{msg.content}</p>
              {msg.sources?.length > 0 && (
                <div className="chat-sources">
                  {msg.sources.map((src, i) => (
                    <span key={i} className="chat-source-tag">
                      {src.label || `Source ${i + 1}`}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
        {isSending && <div className="chat-status">Thinking...</div>}
        <div ref={bottomRef} />
      </div>

      {error && <div className="chat-error">{error}</div>}

      <form className="chat-input-bar" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about this meeting..."
        />
        <button type="submit" disabled={isSending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}