import {
  LayoutDashboard,
  Users,
  MessageSquare,
  ClipboardList,
  Building2,
  Settings,
} from "lucide-react";
import type { NavTab } from "../types";
import { useAgentStore } from "../stores/agentStore";
import logoImg from "../assets/logo.jpg";

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}

const NAV_ITEMS: { id: NavTab; label: string; icon: typeof LayoutDashboard; section?: string }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, section: "Overview" },
  { id: "agents", label: "Agents", icon: Users },
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "tasks", label: "Tasks", icon: ClipboardList, section: "Workspace" },
  { id: "office", label: "Office", icon: Building2 },
  { id: "settings", label: "Settings", icon: Settings, section: "System" },
];

export default function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const agents = useAgentStore((s) => s.agents);
  const onlineCount = agents.filter((a) => a.status === "online" || a.status === "busy").length;

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src={logoImg} alt="Logo" className="sidebar-logo" />
        <div>
          <div className="sidebar-title">PerfectBlue Agent</div>
          <div className="sidebar-subtitle">Multi-Agent Control</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;

          return (
            <div key={item.id}>
              {item.section && (
                <div className="sidebar-section-label">{item.section}</div>
              )}
              <button
                className={`nav-item${activeTab === item.id ? " active" : ""}`}
                onClick={() => onTabChange(item.id)}
              >
                <Icon size={18} className="nav-icon" />
                <span>{item.label}</span>
                {item.id === "agents" && (
                  <span className="nav-badge">{agents.length}</span>
                )}
              </button>
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-footer-avatar">👤</div>
        <div className="sidebar-footer-info">
          <div className="sidebar-footer-name">Workspace</div>
          <div className="sidebar-footer-role">{onlineCount} agents online</div>
        </div>
      </div>
    </aside>
  );
}
