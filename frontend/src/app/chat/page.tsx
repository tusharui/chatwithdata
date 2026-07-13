"use client";

import { Suspense, useEffect, useState, useRef, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { ChartRenderer } from "@/components/ChartRenderer";
import { DataTable } from "@/components/DataTable";

interface Message {
  id: string;
  role: string;
  content: string;
  chart_type: string | null;
  chart_data: unknown;
  table_data: unknown;
  sql_query: string | null;
  created_at: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
}

let _msgCounter = 0;
function nextMsgId(): string {
  _msgCounter += 1;
  return `msg_${Date.now()}_${_msgCounter}`;
}

function ChatContent() {
  const { user, token, isLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const datasetId = searchParams.get("dataset");

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [datasetName, setDatasetName] = useState("");
  const [showSidebar, setShowSidebar] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isLoading && !user) router.push("/login");
  }, [user, isLoading, router]);

  useEffect(() => {
    if (!datasetId || !token) return;
    setLoadError(null);
    api.datasets.get(datasetId, token).then((ds) => setDatasetName(ds.name)).catch(() => setDatasetName("Unknown dataset"));
    api.chat.conversations(datasetId, token).then((res) => setConversations((res.conversations || []) as Conversation[])).catch(() => setLoadError("Failed to load conversations"));
  }, [datasetId, token]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const refreshConversations = useCallback(() => {
    if (!datasetId || !token) return;
    api.chat.conversations(datasetId, token).then((r) => setConversations((r.conversations || []) as Conversation[])).catch(() => {});
  }, [datasetId, token]);

  const loadConversation = useCallback((conv: Conversation) => {
    setActiveConvId(conv.id);
    setMessages(conv.messages || []);
  }, []);

  const handleSend = async () => {
    if (!input.trim() || !token || !datasetId || sending) return;
    const msgId = nextMsgId();
    const userMsg: Message = { id: msgId, role: "user", content: input.trim(), chart_type: null, chart_data: null, table_data: null, sql_query: null, created_at: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);
    try {
      const res = await api.chat.send(datasetId, userMsg.content, activeConvId, token);
      setMessages((prev) => [...prev, res]);
      if (!activeConvId) { setActiveConvId(res.conversation_id); refreshConversations(); }
    } catch (err: unknown) {
      setMessages((prev) => [...prev, { id: nextMsgId(), role: "assistant", content: `Error: ${err instanceof Error ? err.message : "Failed to get response"}`, chart_type: null, chart_data: null, table_data: null, sql_query: null, created_at: new Date().toISOString() }]);
    } finally {
      setSending(false);
    }
  };

  if (isLoading || !user) {
    return <div className="min-h-screen flex items-center justify-center"><div className="w-6 h-6 border-2 border-black border-t-transparent rounded-full animate-spin" /></div>;
  }

  if (!datasetId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm text-neutral-500 mb-4">No dataset selected</p>
          <Link href="/dashboard" className="px-4 py-2 bg-black text-white text-xs font-medium rounded-lg hover:bg-black/80 transition-colors">Go to dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {showSidebar && (
        <aside className="w-64 border-r border-black/10 flex flex-col bg-neutral-50/50">
          <div className="p-4 border-b border-black/10"><Link href="/dashboard" className="text-sm font-bold tracking-tight">ChatWithData</Link></div>
          <div className="p-3"><Link href="/dashboard" className="flex items-center gap-2 text-xs text-neutral-500 hover:text-black transition-colors px-3 py-2">&larr; All datasets</Link></div>
          <div className="px-3 mb-2"><p className="text-[10px] font-medium text-neutral-400 uppercase tracking-wider px-3 mb-1">{datasetName}</p></div>
          {loadError && <div className="px-3 mb-2"><p className="text-[10px] text-red-500 px-3">{loadError}</p></div>}
          <div className="flex-1 overflow-y-auto px-3 space-y-0.5">
            {conversations.map((conv) => (
              <button key={conv.id} onClick={() => loadConversation(conv)} className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors truncate ${activeConvId === conv.id ? "bg-black text-white" : "text-neutral-600 hover:bg-neutral-100"}`}>{conv.title}</button>
            ))}
          </div>
        </aside>
      )}

      <div className="flex-1 flex flex-col">
        <nav className="flex items-center gap-3 px-4 py-3 border-b border-black/10">
          <button onClick={() => setShowSidebar(!showSidebar)} className="p-1.5 hover:bg-neutral-100 rounded-lg transition-colors">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M2 4h12M2 8h12M2 12h12" /></svg>
          </button>
          <div><h2 className="text-sm font-medium">{datasetName}</h2></div>
        </nav>

        <div className="flex-1 overflow-y-auto px-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center mb-4">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
              </div>
              <p className="text-sm font-medium mb-1">Ask anything about your data</p>
              <p className="text-xs text-neutral-500 max-w-sm">Try: &quot;What are the top 5 products by revenue?&quot; or &quot;Show monthly trends&quot;</p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto py-6 space-y-6">
              {messages.map((msg) => (
                <div key={msg.id} className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}>
                  <div className={`max-w-[85%] ${msg.role === "user" ? "bg-black text-white px-4 py-3 rounded-2xl rounded-br-sm text-sm" : "space-y-3 w-full"}`}>
                    {msg.role === "user" ? msg.content : (
                      <>
                        <div className="bg-neutral-50 border border-black/10 px-4 py-3 rounded-2xl rounded-bl-sm text-sm">
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                          {msg.chart_data != null && typeof msg.chart_data === "object" && (
                            <div className="mt-4"><ChartRenderer chartData={msg.chart_data as { type: string; data: { name: string; value: number }[]; title: string }} /></div>
                          )}
                          {msg.table_data != null && typeof msg.table_data === "object" && "rows" in (msg.table_data as Record<string, unknown>) && Array.isArray((msg.table_data as { rows: unknown[] }).rows) && (msg.table_data as { rows: unknown[] }).rows.length > 0 && (
                            <div className="mt-4"><DataTable data={msg.table_data as { rows: Record<string, unknown>[]; total_rows: number }} /></div>
                          )}
                          {msg.sql_query != null && (
                            <details className="mt-3">
                              <summary className="text-[10px] text-neutral-400 cursor-pointer hover:text-neutral-600">View SQL</summary>
                              <pre className="mt-1 text-[11px] bg-black text-white p-3 rounded-lg overflow-x-auto font-mono">{msg.sql_query}</pre>
                            </details>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="bg-neutral-50 border border-black/10 px-4 py-3 rounded-2xl rounded-bl-sm">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-neutral-300 rounded-full animate-bounce [animation-delay:-0.3s]" />
                      <div className="w-2 h-2 bg-neutral-300 rounded-full animate-bounce [animation-delay:-0.15s]" />
                      <div className="w-2 h-2 bg-neutral-300 rounded-full animate-bounce" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="border-t border-black/10 p-4">
          <div className="max-w-3xl mx-auto">
            <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2">
              <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question about your data..." className="flex-1 px-4 py-3 border border-black/20 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-black/20 focus:border-black/40" disabled={sending} />
              <button type="submit" disabled={sending || !input.trim()} className="px-5 py-3 bg-black text-white text-sm font-medium rounded-xl hover:bg-black/80 disabled:opacity-30 transition-colors">Send</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="w-6 h-6 border-2 border-black border-t-transparent rounded-full animate-spin" /></div>}>
      <ChatContent />
    </Suspense>
  );
}
