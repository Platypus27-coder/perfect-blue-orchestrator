import { useState, useRef, useEffect } from "react";
import { Send, MessageSquare } from "lucide-react";
import { useAgentStore, ROLE_LABELS } from "../../stores/agentStore";
import { runtimeFetch } from "../../lib/runtimeApi";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: number;
}

type RuntimeMessage = {
  id?: number;
  role: "user" | "assistant" | "model";
  content: string;
  created_at?: number;
};

const sessionKeyForAgent = (agentId: string) => `agent:${agentId}:main`;

export default function ChatScreen() {
  const { agents, selectedAgentId, selectAgent } = useAgentStore();
  const [messages, setMessages] = useState<Record<string, Message[]>>({});
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const loadedAgentIds = useRef(new Set<string>());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeAgent = agents.find((a) => a.id === selectedAgentId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, selectedAgentId]);

  useEffect(() => {
    if (!selectedAgentId || loadedAgentIds.current.has(selectedAgentId)) return;
    const agentId = selectedAgentId;
    loadedAgentIds.current.add(agentId);
    void runtimeFetch<{ messages: RuntimeMessage[] }>(
      `/sessions/${encodeURIComponent(sessionKeyForAgent(agentId))}/messages`,
    )
      .then((response) => {
        setMessages((previous) => ({
          ...previous,
          [agentId]: response.messages.map((message, index) => ({
            id: String(message.id ?? `${agentId}-${index}`),
            role: message.role === "user" ? "user" : "agent",
            content: message.content,
            timestamp: message.created_at ? message.created_at * 1000 : Date.now(),
          })),
        }));
      })
      .catch(() => {
        loadedAgentIds.current.delete(agentId);
      });
  }, [selectedAgentId]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !selectedAgentId || !activeAgent || sending) return;

    const agentId = selectedAgentId;
    const content = input.trim();
    const existingMessages = messages[agentId] || [];
    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      content,
      timestamp: Date.now(),
    };

    setMessages((prev) => ({
      ...prev,
      [agentId]: [...(prev[agentId] || []), userMsg],
    }));
    setInput("");
    setSending(true);

    try {
      const response = await runtimeFetch<{
        choices: Array<{ message: { content: string } }>;
      }>("/v1/chat/completions", {
        method: "POST",
        body: JSON.stringify({
          model: activeAgent.model,
          role: activeAgent.id,
          session_id: sessionKeyForAgent(agentId),
          messages: [...existingMessages, userMsg].map((message) => ({
            role: message.role === "agent" ? "assistant" : "user",
            content: message.content,
          })),
        }),
      });
      const reply = response.choices[0]?.message.content?.trim();
      if (!reply) throw new Error("Runtime returned an empty response.");
      setMessages((prev) => ({
        ...prev,
        [agentId]: [
          ...(prev[agentId] || []),
          {
            id: `msg-${Date.now()}-assistant`,
            role: "agent",
            content: reply,
            timestamp: Date.now(),
          },
        ],
      }));
    } catch (error) {
      setMessages((prev) => ({
        ...prev,
        [agentId]: [
          ...(prev[agentId] || []),
          {
            id: `msg-${Date.now()}-error`,
            role: "agent",
            content: `Runtime error: ${error instanceof Error ? error.message : "Unknown error"}`,
            timestamp: Date.now(),
          },
        ],
      }));
    } finally {
      setSending(false);
    }
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
                <button className="btn btn-primary" type="submit" disabled={!input.trim() || sending}>
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
