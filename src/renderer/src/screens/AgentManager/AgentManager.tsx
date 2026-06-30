import { useState } from "react";
import { Plus, Trash2, CheckCircle2, Cpu, X } from "lucide-react";
import { useAgentStore, MAX_AGENTS, ROLE_LABELS } from "../../stores/agentStore";
import type { AgentRole } from "../../types";

const ROLES: AgentRole[] = ["developer", "researcher", "writer", "designer", "analyst", "tester", "manager", "custom"];
const MODELS = ["gpt-4o", "claude-4", "gemini-2.5-pro", "llama-4", "deepseek-r1"];

export default function AgentManager() {
  const { agents, addAgent, removeAgent, canAddAgent } = useAgentStore();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: "", role: "developer" as AgentRole, description: "", model: "gpt-4o" });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    addAgent(form);
    setForm({ name: "", role: "developer", description: "", model: "gpt-4o" });
    setShowModal(false);
  }

  function handleDelete(id: string) {
    removeAgent(id);
    setDeleteConfirm(null);
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Agents</h1>
          <p className="page-subtitle">{agents.length} / {MAX_AGENTS} agents configured</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)} disabled={!canAddAgent()}>
          <Plus size={16} /> Add Agent
        </button>
      </div>

      <div className="page-body">
        <div className="agents-grid">
          {agents.map((agent) => (
            <div key={agent.id} className="agent-card">
              <div className="agent-card-top">
                <div className="agent-avatar" style={{ background: agent.avatar }}>
                  {agent.name[0]}
                  <span className={`agent-status-dot ${agent.status}`} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="agent-name">{agent.name}</div>
                  <div className="agent-role">{ROLE_LABELS[agent.role]}</div>
                </div>
                {deleteConfirm === agent.id ? (
                  <div style={{ display: "flex", gap: 4 }}>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDelete(agent.id)} style={{ padding: "4px 8px" }}>
                      Yes
                    </button>
                    <button className="btn btn-ghost btn-sm" onClick={() => setDeleteConfirm(null)} style={{ padding: "4px 8px" }}>
                      No
                    </button>
                  </div>
                ) : (
                  <button className="btn btn-icon btn-ghost" onClick={() => setDeleteConfirm(agent.id)} title="Delete">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
              <p className="agent-desc">{agent.description}</p>
              <div className="agent-meta">
                <span className="agent-meta-item"><Cpu size={12} /> {agent.model}</span>
                <span className="agent-meta-item"><CheckCircle2 size={12} /> {agent.tasksCompleted} done</span>
              </div>
              {agent.currentTask && (
                <div className="agent-task-badge">⚡ {agent.currentTask}</div>
              )}
            </div>
          ))}

          {canAddAgent() && (
            <div className="agent-card-add" onClick={() => setShowModal(true)}>
              <Plus size={28} />
              <span style={{ fontSize: 13, fontWeight: 500 }}>Add Agent</span>
              <span style={{ fontSize: 11 }}>{MAX_AGENTS - agents.length} slots remaining</span>
            </div>
          )}
        </div>
      </div>

      {/* Add Agent Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h2 className="modal-title" style={{ margin: 0 }}>New Agent</h2>
              <button className="btn btn-icon btn-ghost" onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Name</label>
                <input className="form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Atlas" autoFocus />
              </div>
              <div className="form-group">
                <label className="form-label">Role</label>
                <select className="form-select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as AgentRole })}>
                  {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Model</label>
                <select className="form-select" value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })}>
                  {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea className="form-textarea" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="What does this agent do?" />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={!form.name.trim()}>Create Agent</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
