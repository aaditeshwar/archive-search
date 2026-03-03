import React, { useEffect, useMemo, useState } from "react";
import { createSession, search, type SearchChunk } from "./api";

type ChatMsg = { role: "user" | "assistant"; content: string };

export function App() {
  const [sessionId, setSessionId] = useState<string>("");
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chunks, setChunks] = useState<SearchChunk[]>([]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const s = await createSession();
        setSessionId(s.session_id);
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    })();
  }, []);

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  async function onSend() {
    const q = input.trim();
    if (!q) return;
    setInput("");
    setError(null);
    setLoading(true);
    setAnswer(null);
    setChunks([]);
    setMsgs((m) => [...m, { role: "user", content: q }]);

    try {
      const res = await search(q, 10, true);
      setChunks(res.chunks || []);
      setAnswer(res.answer || null);
      setMsgs((m) => [
        ...m,
        {
          role: "assistant",
          content: res.answer?.trim() || "Here are the most relevant results I found.",
        },
      ]);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <div>
          <div className="title">Archive Search</div>
          <div className="subtitle">Natural language search over Google Groups + linked content</div>
        </div>
        <div className="session">Session: {sessionId || "…"}</div>
      </header>

      <main className="main">
        <section className="chat">
          <div className="messages">
            {msgs.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                <div className="role">{m.role}</div>
                <div className="bubble">{m.content}</div>
              </div>
            ))}
            {loading && <div className="hint">Searching…</div>}
            {error && <div className="error">{error}</div>}
          </div>

          <div className="composer">
            <input
              className="input"
              placeholder="Ask a question about the mailing list…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onSend();
              }}
            />
            <button className="button" disabled={!canSend} onClick={onSend}>
              Send
            </button>
          </div>
        </section>

        <aside className="results">
          <div className="resultsHeader">Top matches</div>
          {answer && (
            <div className="answer">
              <div className="resultsTitle">Answer</div>
              <div className="answerText">{answer}</div>
            </div>
          )}
          {chunks.length === 0 && <div className="hint">No results yet.</div>}
          {chunks.map((c, idx) => (
            <div key={idx} className="card">
              <div className="cardTitle">
                {c.title || c.source_type}{" "}
                {typeof c.score === "number" ? <span className="score">{c.score.toFixed(3)}</span> : null}
              </div>
              <div className="cardMeta">
                {c.message_url ? (
                  <a href={c.message_url} target="_blank" rel="noreferrer">
                    Message
                  </a>
                ) : null}
                {c.linked_url ? (
                  <>
                    {" · "}
                    <a href={c.linked_url} target="_blank" rel="noreferrer">
                      Linked
                    </a>
                  </>
                ) : null}
              </div>
              <div className="cardText">{c.text}</div>
            </div>
          ))}
        </aside>
      </main>
    </div>
  );
}

