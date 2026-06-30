/* =========================================================================
   Multi-Agent Dashboard — Core Types
   ========================================================================= */

export type AgentStatus = "online" | "busy" | "offline" | "error";

export type AgentRole =
  | "developer"
  | "researcher"
  | "writer"
  | "designer"
  | "analyst"
  | "tester"
  | "manager"
  | "custom";

export interface Agent {
  id: string;
  name: string;
  role: AgentRole;
  description: string;
  status: AgentStatus;
  avatar: string; // hex color for avatar circle
  model: string;
  currentTask: string | null;
  tasksCompleted: number;
  createdAt: number;
}

export type TaskPriority = "high" | "medium" | "low";
export type TaskStatus = "backlog" | "in_progress" | "review" | "done";

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  assigneeId: string | null;
  createdAt: number;
  updatedAt: number;
}

export interface ChatMessage {
  id: string;
  agentId: string;
  role: "user" | "agent";
  content: string;
  timestamp: number;
}

export type NavTab =
  | "dashboard"
  | "agents"
  | "chat"
  | "tasks"
  | "office"
  | "settings";
