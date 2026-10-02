"use client";

import { type FormEvent, useState } from "react";
import type { AskResponse, ToolCall } from "./types";

interface Exchange {
  question: string;
  response?: AskResponse;
  error?: string;
}

export default function ChatPage() {
  const [question, setQuestion] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [pending, setPending] = useState(false);

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (!text || pending) return;
    setPending(true);
    setQuestion("");
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question: text, session_id: sessionId }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : res.statusText);
      const response = body as AskResponse;
      setSessionId(response.session_id);
      setExchanges((prev) => [...prev, { question: text, response }]);
    } catch (err) {
      const error = err instanceof Error ? err.message : String(err);
      setExchanges((prev) => [...prev, { question: text, error }]);
    } finally {
      setPending(false);
    }
  }

  return (
    <main>
      <h1>TestLens</h1>
      <p className="muted">Ask about drive SMART telemetry and failure-prediction scores.</p>

      {exchanges.map((exchange, i) => (
        <section key={i} className="exchange">
          <p className="question">{exchange.question}</p>
          {exchange.error && <p className="error">{exchange.error}</p>}
          {exchange.response && (
            <>
              <p className="answer">{exchange.response.answer}</p>
              {exchange.response.tool_calls.map((call, j) => (
                <ToolCallResult key={j} call={call} />
              ))}
            </>
          )}
        </section>
      ))}

      <form onSubmit={ask}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Which drives are most likely to fail in the next 30 days?"
          aria-label="Question"
        />
        <button type="submit" disabled={pending || !question.trim()}>
          {pending ? "Asking..." : "Ask"}
        </button>
      </form>
    </main>
  );
}

function ToolCallResult({ call }: { call: ToolCall }) {
  const columns = call.rows.length > 0 ? Object.keys(call.rows[0]) : [];
  return (
    <details className="tool-call">
      <summary>
        <code>
          {call.tool}({JSON.stringify(call.arguments)})
        </code>{" "}
        <span className="muted">
          {call.error ? "error" : `${call.rows.length} rows${call.cached ? ", cached" : ""}`}
        </span>
      </summary>
      {call.error && <p className="error">{call.error}</p>}
      {columns.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {call.rows.map((row, r) => (
                <tr key={r}>
                  {columns.map((c) => (
                    <td key={c}>{row[c] === null ? "" : String(row[c])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </details>
  );
}
