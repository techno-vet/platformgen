"use client";
import { useEffect, useRef, useState } from "react";

interface Message {
  role: "user" | "step" | "assistant" | "error";
  text: string;
}

interface Widget {
  id: string;
  title: string;
  purpose: string;
  unlocked: boolean;
  deps_met: boolean;
  depends_on: string[];
  in_progress: boolean;
}

// Desktop button — computes VNC URL in onClick (direct user gesture = no popup blocker)
function DesktopLink() {
  return (
    <button
      onClick={() => {
        const proxyBase = window.location.pathname.replace(/\/proxy\/\d+\/?.*$/, "");
        const wsPath = encodeURIComponent(`user${proxyBase}/proxy/6080/websockify`);
        const url = `${window.location.origin}${proxyBase}/proxy/6080/vnc.html?autoconnect=true&resize=scale&path=${wsPath}`;
        window.open(url, "_blank");
      }}
      className="text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded border border-gray-600"
      title="Open Genny desktop (tkinter platform)"
    >
      🖥️ Desktop
    </button>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", text: "👋 Hi, I'm **Genny**. Tell me what you want to build — or pick a widget on the left to get started." },
  ]);
  const [input, setInput] = useState("");
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [connected, setConnected] = useState(false);
  const [thinking, setThinking] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load widget manifest
  useEffect(() => {
    // Use relative-to-page URL so it works both in dev and behind JupyterHub proxy
    // e.g. /user/techno-vet/proxy/8889/api/widgets
    const base = window.location.href.endsWith("/") ? window.location.href : window.location.href + "/";
    const apiUrl = new URL("api/widgets", base).toString();
    fetch(apiUrl)
      .then((r) => r.json())
      .then((d) => setWidgets(d.widgets || []))
      .catch(() => {});
  }, []);

  // Connect WebSocket
  useEffect(() => {
    // Derive WS URL from current page location — handles JupyterHub proxy prefix automatically
    // e.g. wss://platformgen.ai/user/techno-vet/proxy/8889/ws/chat
    // Ensure trailing slash so relative URL resolves correctly
    const base = window.location.href.endsWith("/") ? window.location.href : window.location.href + "/";
    const wsUrl = new URL("ws/chat", base);
    wsUrl.protocol = wsUrl.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(wsUrl.toString());
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "step") {
        setMessages((prev) => [...prev, { role: "step", text: msg.text }]);
      } else if (msg.type === "done") {
        setThinking(false);
        setMessages((prev) => [...prev, { role: "assistant", text: msg.text }]);
      } else if (msg.type === "error") {
        setThinking(false);
        setMessages((prev) => [...prev, { role: "error", text: msg.text }]);
      }
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = () => {
    if (!input.trim() || !connected || thinking) return;
    const prompt = input.trim();
    setInput("");
    setThinking(true);
    setMessages((prev) => [...prev, { role: "user", text: prompt }]);
    wsRef.current?.send(JSON.stringify({ prompt }));
  };

  const askAboutWidget = (w: Widget) => {
    const prompt = w.unlocked
      ? `Help me use the ${w.title} widget. ${w.purpose}`
      : `I want to unlock the ${w.title} widget. What do I need to do first?`;
    setInput(prompt);
  };

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 font-mono text-sm">
      {/* Left panel — Lego widget tree */}
      <div className="w-72 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="px-4 py-3 bg-blue-700 font-bold text-white text-base">
          🧩 Platform Widgets
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {widgets.map((w) => (
            <button
              key={w.id}
              onClick={() => askAboutWidget(w)}
              className={`w-full text-left px-3 py-2 rounded border transition-all ${
                w.unlocked
                  ? "bg-gray-800 border-green-700 hover:bg-gray-700 text-green-300"
                  : w.deps_met
                  ? "bg-gray-800 border-yellow-600 hover:bg-gray-700 text-yellow-300"
                  : "bg-gray-900 border-gray-700 text-gray-500 cursor-not-allowed opacity-60"
              }`}
              title={w.purpose}
            >
              <div className="flex items-center gap-2">
                <span>{w.unlocked ? "✅" : w.deps_met ? "🔓" : "🔒"}</span>
                <span className="font-semibold">{w.title}</span>
              </div>
              {w.depends_on.length > 0 && !w.unlocked && (
                <div className="text-xs text-gray-500 mt-0.5 pl-6">
                  needs: {w.depends_on.join(", ")}
                </div>
              )}
            </button>
          ))}
          {widgets.length === 0 && (
            <div className="text-gray-600 px-3 py-4 text-xs">Loading widgets...</div>
          )}
        </div>
      </div>

      {/* Right panel — chat */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="px-4 py-2 bg-gray-900 border-b border-gray-800 flex items-center gap-3">
          <span className="text-blue-400 font-bold text-base">✨ Ask Genny</span>
          <span className={`text-xs px-2 py-0.5 rounded ${connected ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
            {connected ? "● connected" : "● disconnected"}
          </span>
          {thinking && <span className="text-yellow-400 text-xs animate-pulse">⏳ Genny is thinking...</span>}
          <div className="ml-auto">
            <DesktopLink />
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-2xl px-4 py-2 rounded-lg whitespace-pre-wrap text-sm ${
                m.role === "user"       ? "bg-blue-700 text-white"
                : m.role === "step"    ? "bg-purple-950 text-purple-300 border border-purple-800 font-mono text-xs"
                : m.role === "error"   ? "bg-red-950 text-red-300 border border-red-800"
                : "bg-gray-800 text-gray-100"
              }`}>
                {m.role === "step" && <span className="text-purple-400 mr-2">🔧</span>}
                {m.text}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="p-3 border-t border-gray-800 bg-gray-900 flex gap-2">
          <textarea
            className="flex-1 bg-gray-800 text-gray-100 rounded px-3 py-2 resize-none border border-gray-700 focus:outline-none focus:border-blue-500 text-sm"
            rows={2}
            placeholder="Ask Genny anything… or describe what you want to build"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
            }}
          />
          <button
            onClick={send}
            disabled={!connected || thinking || !input.trim()}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded font-bold transition-colors"
          >
            Ask ➤
          </button>
        </div>
      </div>
    </div>
  );
}
