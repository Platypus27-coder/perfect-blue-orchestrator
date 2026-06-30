import { useState, useRef, useEffect } from "react";
import { Send, MessageSquare } from "lucide-react";
import { useAgentStore, ROLE_LABELS } from "../../stores/agentStore";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: number;
}

const DEMO_REPLIES = [
  "I understand your request. Let me work on that right away.",
  "Good question! Based on my analysis, here's what I recommend...",
  "I've completed the task. The results look promising — shall I elaborate?",
  "Processing your request. This might take a moment due to complexity.",
  "Here's a summary of my findings from the latest research data.",
];

export default function ChatScreen() {
  const { agents, selectedAgentId, selectAgent } = useAgentStore();
  const [messages, setMessages] = useState<Record<string, Message[]>>({});
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeAgent = agents.find((a) => a.id === selectedAgentId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, selectedAgentId]);

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !selectedAgentId) return;

    const userMsg: Message = { id: `msg-${Date.now()}`, role: "user", content: input.trim(), timestamp: Date.now() };
    const agentReply: Message = {
      id: `msg-${Date.now() + 1}`,
      role: "agent",
      content: DEMO_REPLIES[Math.floor(Math.random() * DEMO_REPLIES.length)],
      timestamp: Date.now() + 1000,
    };

    setMessages((prev) => ({
      ...prev,
      [selectedAgentId]: [...(prev[selectedAgentId] || []), userMsg, agentReply],
    }));
    setInput("");
  }

  const currentMessages = selectedAgentId ? messages[selectedAgentId] || [] : [];

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Chat</h1>
          <p className="page-subtitle">
            {activeAgent ? `Talking to ${activeAgent.name}` : "Select an agent to start chatting"}
          </p>
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Agent List */}
        <div style={{
          width: 220,
          borderRight: "1px solid var(--border)",
          overflowY: "auto",
          padding: "12px 8px",
          flexShrink: 0,
        }}>
          {agents.map((agent) => (
            <button
              key={agent.id}
              className={`nav-item${selectedAgentId === agent.id ? " active" : ""}`}
              onClick={() => selectAgent(agent.id)}
              style={{ marginBottom: 2 }}
            >
              <div className="agent-avatar agent-avatar-sm" style={{ background: agent.avatar, fontSize: 10 }}>
                {agent.name[0]}
              </div>
              <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{agent.name}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{ROLE_LABELS[agent.role]}</div>
              </div>
              <span className={`status-dot-inline ${agent.status}`} />
            </button>
          ))}
        </div>

        {/* Chat Area */}
        <div className="chat-container" style={{ flex: 1 }}>
          {activeAgent ? (
            <>
              <div className="chat-messages">
                {currentMessages.length === 0 && (
                  <div className="empty-state">
                    <MessageSquare size={40} className="empty-state-icon" />
                    <div className="empty-state-title">Start a conversation</div>
                    <div className="empty-state-desc">
                      Send a message to {activeAgent.name} to begin
                    </div>
                  </div>
                )}
                {currentMessages.map((msg) => (
                  <div key={msg.id} className={`chat-bubble ${msg.role}`}>
                    {msg.content}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              <form className="chat-input-area" onSubmit={handleSend}>
                <input
                  className="chat-input"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={`Message ${activeAgent.name}...`}
                />
                <button className="btn btn-primary" type="submit" disabled={!input.trim()}>
                  <Send size={16} />
                </button>
              </form>
            </>
          ) : (
            <div className="empty-state" style={{ height: "100%" }}>
              <MessageSquare size={48} className="empty-state-icon" />
              <div className="empty-state-title">No agent selected</div>
              <div className="empty-state-desc">
                Choose an agent from the list to start chatting
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
