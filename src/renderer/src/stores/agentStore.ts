import { create } from "zustand";
import type { Agent, AgentRole, AgentStatus } from "../types";

const MAX_AGENTS = 8;

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

// --- Demo agents ---
const demoAgents: Agent[] = [
  {
    id: "agent-1",
    name: "Atlas",
    role: "developer",
    description: "Full-stack developer specializing in React & Node.js",
    status: "online",
    avatar: AVATAR_COLORS[0],
    model: "gpt-4o",
    currentTask: "Build authentication module",
    tasksCompleted: 14,
    createdAt: Date.now() - 7 * 86400000,
  },
  {
    id: "agent-2",
    name: "Nova",
    role: "researcher",
    description: "Deep research agent for market analysis and data mining",
    status: "busy",
    avatar: AVATAR_COLORS[1],
    model: "claude-4",
    currentTask: "Analyze competitor landscape",
    tasksCompleted: 8,
    createdAt: Date.now() - 5 * 86400000,
  },
  {
    id: "agent-3",
    name: "Echo",
    role: "writer",
    description: "Content creation, documentation and technical writing",
    status: "online",
    avatar: AVATAR_COLORS[2],
    model: "gpt-4o",
    currentTask: null,
    tasksCompleted: 22,
    createdAt: Date.now() - 10 * 86400000,
  },
  {
    id: "agent-4",
    name: "Cipher",
    role: "analyst",
    description: "Data analysis, visualization, and business intelligence",
    status: "offline",
    avatar: AVATAR_COLORS[3],
    model: "gemini-2.5-pro",
    currentTask: null,
    tasksCompleted: 6,
    createdAt: Date.now() - 3 * 86400000,
  },
];

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
  removeAgent: (id: string) => void;
  updateAgent: (id: string, updates: Partial<Agent>) => void;
  setStatus: (id: string, status: AgentStatus) => void;
  selectAgent: (id: string | null) => void;
  getAgent: (id: string) => Agent | undefined;
  fetchAgents: () => Promise<void>;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: demoAgents,
  selectedAgentId: null,

  canAddAgent: () => get().agents.length < MAX_AGENTS,

  addAgent: async (data) => {
    const { agents } = get();
    if (agents.length >= MAX_AGENTS) return;

    const usedColors = agents.map((a) => a.avatar);
    const availableColor =
      AVATAR_COLORS.find((c) => !usedColors.includes(c)) || AVATAR_COLORS[0];

    const newId = data.name.toLowerCase().replace(/[^a-z0-9]/g, '-');

    const newAgent: Agent = {
      id: newId,
      name: data.name,
      role: data.role,
      description: data.description,
      status: "online",
      avatar: availableColor,
      model: data.model,
      currentTask: null,
      tasksCompleted: 0,
      createdAt: Date.now(),
    };

    set({ agents: [...agents, newAgent] });

    try {
      await fetch("http://127.0.0.1:7770/agents/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: newId,
          role: data.role,
          name: data.name,
          description: data.description,
          model: data.model
        })
      });
    } catch (err) {
      console.error("Failed to sync new agent to backend:", err);
    }
  },

  removeAgent: (id) => {
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
      const res = await fetch("http://127.0.0.1:7770/state");
      if (!res.ok) return;
      const data = await res.json();
      const active = data.active || {};
      
      const { agents: currentAgents } = get();
      
      const backendRoleToFrontendRole: Record<string, AgentRole> = {
        programmer: "developer",
        qa: "tester",
        designer: "designer",
        manager: "manager",
        researcher: "researcher",
        writer: "writer",
        support: "custom",
        devops: "custom",
        security: "custom"
      };
      
      const newAgents: Agent[] = Object.keys(active).map((roleId, idx) => {
        const id = roleId;
        const mappedRole: AgentRole = backendRoleToFrontendRole[id] || "custom";
        const name = id.charAt(0).toUpperCase() + id.slice(1);
        
        const existing = currentAgents.find(a => a.id === id || a.name.toLowerCase() === id.toLowerCase());
        if (existing) {
          return { ...existing, id, model: active[id], status: "online" };
        }
        
        return {
          id,
          name,
          role: mappedRole,
          description: `Backend agent: ${name}`,
          status: "online",
          avatar: AVATAR_COLORS[idx % AVATAR_COLORS.length],
          model: active[id] || "default",
          currentTask: null,
          tasksCompleted: 0,
          createdAt: Date.now(),
        };
      });
      
      set({ agents: newAgents });
    } catch (err) {
      console.error("Failed to fetch backend agents:", err);
    }
  },
}));

export { MAX_AGENTS, AVATAR_COLORS, ROLE_LABELS };
