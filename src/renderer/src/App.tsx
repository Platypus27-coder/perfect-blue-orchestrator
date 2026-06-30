import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./screens/Dashboard/Dashboard";
import AgentManager from "./screens/AgentManager/AgentManager";
import ChatScreen from "./screens/ChatScreen/ChatScreen";
import OfficeScreen from "./screens/OfficeScreen/OfficeScreen";
import SettingsScreen from "./screens/SettingsScreen/SettingsScreen";
import type { NavTab } from "./types";

function App() {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");

  function renderScreen() {
    switch (activeTab) {
      case "dashboard":
        return <Dashboard />;
      case "agents":
        return <AgentManager />;
      case "chat":
        return <ChatScreen />;
      case "tasks":
        return (
          <div className="main-content">
            <div className="page-header">
              <div>
                <h1 className="page-title">Tasks</h1>
                <p className="page-subtitle">Kanban board — coming soon</p>
              </div>
            </div>
            <div className="page-body">
              <div className="empty-state">
                <div className="empty-state-title">Task Board</div>
                <div className="empty-state-desc">
                  Drag-and-drop kanban board with Backlog, In Progress, Review, and Done columns will be available in the next update.
                </div>
              </div>
            </div>
          </div>
        );
      case "office":
        return <OfficeScreen />;
      case "settings":
        return <SettingsScreen />;
    }
  }

  return (
    <div className="app-shell">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="main-content">
        {renderScreen()}
      </main>
    </div>
  );
}

export default App;
