import { useEffect, useState } from "react";
import { ClipboardList, Plus, Trash2, X } from "lucide-react";

import { runtimeFetch } from "../../lib/runtimeApi";
import { useAgentStore } from "../../stores/agentStore";

type RuntimeTaskStatus = "todo" | "in_progress" | "review" | "done" | "failed";

type RuntimeTask = {
  id: number;
  title: string;
  description: string;
  status: RuntimeTaskStatus;
  assignee_id: string | null;
  created_at: number;
  updated_at: number;
};

const COLUMNS: Array<{ status: RuntimeTaskStatus; label: string }> = [
  { status: "todo", label: "To do" },
  { status: "in_progress", label: "In progress" },
  { status: "review", label: "Review" },
  { status: "done", label: "Done" },
];

export default function TaskScreen() {
  const agents = useAgentStore((state) => state.agents);
  const [tasks, setTasks] = useState<RuntimeTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", description: "", assigneeId: "" });

  useEffect(() => {
    let active = true;
    void runtimeFetch<{ tasks: RuntimeTask[] }>("/api/v1/tasks")
      .then((response) => {
        if (!active) return;
        setTasks(response.tasks);
        setError(null);
      })
      .catch((loadError: unknown) => {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : "Could not load tasks.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function createTask(event: React.FormEvent) {
    event.preventDefault();
    if (!form.title.trim() || saving) return;
    setSaving(true);
    setError(null);
    try {
      const response = await runtimeFetch<{ task: RuntimeTask }>("/api/v1/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: form.title.trim(),
          description: form.description.trim(),
          assignee_id: form.assigneeId || null,
          status: "todo",
        }),
      });
      setTasks((current) => [...current, response.task]);
      setForm({ title: "", description: "", assigneeId: "" });
      setShowModal(false);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not create task.");
    } finally {
      setSaving(false);
    }
  }

  async function updateStatus(task: RuntimeTask, status: RuntimeTaskStatus) {
    const previousStatus = task.status;
    setTasks((current) =>
      current.map((item) => (item.id === task.id ? { ...item, status } : item)),
    );
    try {
      await runtimeFetch(`/api/v1/tasks/${task.id}`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
    } catch (updateError) {
      setTasks((current) =>
        current.map((item) =>
          item.id === task.id ? { ...item, status: previousStatus } : item,
        ),
      );
      setError(updateError instanceof Error ? updateError.message : "Could not update task.");
    }
  }

  async function deleteTask(taskId: number) {
    try {
      await runtimeFetch(`/api/v1/tasks/${taskId}`, { method: "DELETE" });
      setTasks((current) => current.filter((task) => task.id !== taskId));
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Could not delete task.");
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Tasks</h1>
          <p className="page-subtitle">Persistent work queue shared with the runtime</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={16} /> Add Task
        </button>
      </div>

      <div className="page-body">
        {error && (
          <div className="agent-task-badge" style={{ marginBottom: 16, color: "var(--error)" }}>
            {error}
          </div>
        )}
        {loading ? (
          <div className="empty-state-desc">Loading tasks...</div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, minmax(220px, 1fr))",
              gap: 14,
              alignItems: "start",
              overflowX: "auto",
            }}
          >
            {COLUMNS.map((column) => {
              const columnTasks = tasks.filter((task) => task.status === column.status);
              return (
                <section className="card" key={column.status} style={{ minWidth: 220 }}>
                  <div className="card-header">
                    <h3 className="card-title">{column.label}</h3>
                    <span className="nav-badge">{columnTasks.length}</span>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {columnTasks.map((task) => {
                      const assignee = agents.find((agent) => agent.id === task.assignee_id);
                      return (
                        <article
                          key={task.id}
                          style={{
                            border: "1px solid var(--border)",
                            borderRadius: 8,
                            padding: 12,
                            background: "var(--bg-hover)",
                          }}
                        >
                          <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                            <div style={{ flex: 1 }}>
                              <div className="agent-name">{task.title}</div>
                              {task.description && <p className="agent-desc">{task.description}</p>}
                            </div>
                            <button
                              className="btn btn-icon btn-ghost"
                              onClick={() => void deleteTask(task.id)}
                              title="Delete task"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                          <div className="agent-role" style={{ marginBottom: 8 }}>
                            {assignee ? `Assigned to ${assignee.name}` : "Unassigned"}
                          </div>
                          <select
                            className="form-select"
                            value={task.status}
                            onChange={(event) =>
                              void updateStatus(task, event.target.value as RuntimeTaskStatus)
                            }
                          >
                            {COLUMNS.map((option) => (
                              <option key={option.status} value={option.status}>
                                {option.label}
                              </option>
                            ))}
                            <option value="failed">Failed</option>
                          </select>
                        </article>
                      );
                    })}
                    {columnTasks.length === 0 && (
                      <div className="empty-state-desc">No tasks</div>
                    )}
                  </div>
                </section>
              );
            })}
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <ClipboardList size={18} />
                <h2 className="modal-title" style={{ margin: 0 }}>New Task</h2>
              </div>
              <button className="btn btn-icon btn-ghost" onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={createTask}>
              <div className="form-group">
                <label className="form-label">Title</label>
                <input
                  className="form-input"
                  value={form.title}
                  onChange={(event) => setForm({ ...form, title: event.target.value })}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea
                  className="form-textarea"
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Assignee</label>
                <select
                  className="form-select"
                  value={form.assigneeId}
                  onChange={(event) => setForm({ ...form, assigneeId: event.target.value })}
                >
                  <option value="">Unassigned</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>{agent.name}</option>
                  ))}
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" type="submit" disabled={!form.title.trim() || saving}>
                  {saving ? "Creating..." : "Create Task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
