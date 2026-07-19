import { create } from "zustand";
import type { Agent, AgentRole, AgentStatus } from "../types";
import { runtimeFetch } from "../lib/runtimeApi";

const MAX_AGENTS = 32;

const AVATAR_COLORS = [
  "#6b8cce", // cornflower blue
  "#a5b4fc", // lavender
  "#f87171", // coral (koi)
  "#34d399", // emerald
  "#fbbf24", // amber
  "#c084fc", // violet
  "#fb923c", // orange
  "#38bdf8", // sky
];

const ROLE_LABELS: Record<AgentRole, string> = {
  developer: "Developer",
  researcher: "Researcher",
  writer: "Writer",
  designer: "Designer",
  analyst: "Analyst",
  tester: "Tester",
  manager: "Manager",
  custom: "Custom",
};

type RuntimeAgent = {
  id: string;
  name?: string;
  role?: string;
  description?: string;
  status?: string;
  model: string;
  created_at?: number;
};

const backendRoleToFrontendRole: Record<string, AgentRole> = {
  programmer: "developer",
  developer: "developer",
  qa: "tester",
  tester: "tester",
  designer: "designer",
  manager: "manager",
  researcher: "researcher",
  writer: "writer",
  analyst: "analyst",
};

function normalizeRuntimeAgent(agent: RuntimeAgent, index: number): Agent {
  const status: AgentStatus = ["online", "busy", "offline", "error"].includes(
    agent.status ?? "",
  )
    ? (agent.status as AgentStatus)
    : "online";
  return {
    id: agent.id,
    name: agent.name?.trim() || agent.id.charAt(0).toUpperCase() + agent.id.slice(1),
    role: backendRoleToFrontendRole[agent.role ?? agent.id] || "custom",
    description: agent.description?.trim() || `Backend agent: ${agent.id}`,
    status,
    avatar: AVATAR_COLORS[index % AVATAR_COLORS.length],
    model: agent.model,
    currentTask: null,
    tasksCompleted: 0,
    createdAt: agent.created_at ? agent.created_at * 1000 : Date.now(),
  };
}

interface AgentStore {
  agents: Agent[];
  selectedAgentId: string | null;
  canAddAgent: () => boolean;
  addAgent: (data: {
    name: string;
    role: AgentRole;
    description: string;
    model: string;
  }) => Promise<void>;
  removeAgent: (id: string) => Promise<void>;
  updateAgent: (id: string, updates: Partial<Agent>) => void;
  setStatus: (id: string, status: AgentStatus) => void;
  selectAgent: (id: string | null) => void;
  getAgent: (id: string) => Agent | undefined;
  fetchAgents: () => Promise<void>;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: [],
  selectedAgentId: null,

  canAddAgent: () => get().agents.length < MAX_AGENTS,

  addAgent: async (data) => {
    const { agents } = get();
    if (agents.length >= MAX_AGENTS) throw new Error("Agent limit reached.");
    const newId = data.name.toLowerCase().replace(/[^a-z0-9]/g, '-');
    if (!newId) throw new Error("Agent name must contain letters or numbers.");
    const response = await runtimeFetch<{ agent: RuntimeAgent }>("/agents/add", {
      method: "POST",
      body: JSON.stringify({
          id: newId,
          role: data.role,
          name: data.name,
          description: data.description,
          model: data.model,
      }),
    });
    const newAgent = normalizeRuntimeAgent(response.agent, agents.length);
    set({ agents: [...agents.filter((agent) => agent.id !== newId), newAgent] });
  },

  removeAgent: async (id) => {
    await runtimeFetch(`/agents/${encodeURIComponent(id)}`, { method: "DELETE" });
    set((state) => ({
      agents: state.agents.filter((a) => a.id !== id),
      selectedAgentId:
        state.selectedAgentId === id ? null : state.selectedAgentId,
    }));
  },

  updateAgent: (id, updates) => {
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, ...updates } : a)),
    }));
  },

  setStatus: (id, status) => {
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, status } : a)),
    }));
  },

  selectAgent: (id) => set({ selectedAgentId: id }),

  getAgent: (id) => get().agents.find((a) => a.id === id),

  fetchAgents: async () => {
    try {
      const data = await runtimeFetch<{
        agents?: RuntimeAgent[];
        active?: Record<string, string>;
      }>("/state");
      const runtimeAgents =
        data.agents ??
        Object.entries(data.active ?? {}).map(([id, model]) => ({ id, model }));
      const newAgents = runtimeAgents.map(normalizeRuntimeAgent);
      set({ agents: newAgents });
    } catch (error) {
      console.error("Failed to fetch backend agents:", error);
    }
  },
}));

export { MAX_AGENTS, AVATAR_COLORS, ROLE_LABELS };
