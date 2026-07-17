import { useEffect, useState } from "react";
import { Users, CheckCircle2, Activity, Zap } from "lucide-react";
import { useAgentStore, ROLE_LABELS } from "../../stores/agentStore";
import type { AgentStatus } from "../../types";

const STATUS_LABELS: Record<AgentStatus, string> = {
  online: "Online",
  busy: "Busy",
  offline: "Offline",
  error: "Error",
};

export default function Dashboard() {
  const agents = useAgentStore((s) => s.agents);
  const online = agents.filter((a) => a.status === "online" || a.status === "busy").length;
  const totalTasks = agents.reduce((s, a) => s + a.tasksCompleted, 0);
  const busyAgents = agents.filter((a) => a.status === "busy").length;

  const [activities, setActivities] = useState<any[]>([]);

  useEffect(() => {
    // Polling backend every 3 seconds to get real-time activity
    const fetchActivities = async () => {
      try {
        const res = await fetch("http://localhost:7770/api/v1/activities");
        if (res.ok) {
          const data = await res.json();
          if (data.activities) {
            setActivities(data.activities);
          }
        }
      } catch (err) {
        // Silent fail if backend is offline
      }
    };
    
    fetchActivities();
    const interval = setInterval(fetchActivities, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Overview of your multi-agent workspace</p>
        </div>
      </div>

      <div className="page-body">
        {/* Stats */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon" style={{ background: "var(--accent-glow)", color: "var(--accent)" }}>
              <Users size={18} />
            </div>
            <div className="stat-value">{agents.length}</div>
            <div className="stat-label">Total Agents</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: "var(--success-bg)", color: "var(--success)" }}>
              <Activity size={18} />
            </div>
            <div className="stat-value">{online}</div>
            <div className="stat-label">Online Now</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: "var(--warning-bg)", color: "var(--warning)" }}>
              <Zap size={18} />
            </div>
            <div className="stat-value">{busyAgents}</div>
            <div className="stat-label">Working</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: "rgba(165,180,252,0.12)", color: "var(--lavender)" }}>
              <CheckCircle2 size={18} />
            </div>
            <div className="stat-value">{totalTasks}</div>
            <div className="stat-label">Tasks Done</div>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {/* Agent Overview */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Agent Status</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {agents.map((agent) => (
                <div key={agent.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <div className="agent-avatar agent-avatar-sm" style={{ background: agent.avatar }}>
                    {agent.name[0]}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="agent-name" style={{ fontSize: 13 }}>{agent.name}</div>
                    <div className="agent-role">{ROLE_LABELS[agent.role]}</div>
                  </div>
                  <span className={`status-badge ${agent.status}`}>
                    <span className={`status-dot-inline ${agent.status}`} />
                    {STATUS_LABELS[agent.status]}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Activity Feed */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Recent Activity</h3>
            </div>
            <div className="activity-list">
              {activities.map((act, i) => (
                <div key={i} className="activity-item">
                  <div className="agent-avatar agent-avatar-sm" style={{
                    background: agents.find((a) => a.name === act.agent)?.avatar || "var(--accent)",
                    fontSize: 10,
                  }}>
                    {act.agent[0]}
                  </div>
                  <div>
                    <div className="activity-text">
                      <strong>{act.agent}</strong> {act.action} {act.detail && <em>{act.detail}</em>}
                    </div>
                    <div className="activity-time">{act.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
