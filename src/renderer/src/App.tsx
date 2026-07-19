import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./screens/Dashboard/Dashboard";
import AgentManager from "./screens/AgentManager/AgentManager";
import ChatScreen from "./screens/ChatScreen/ChatScreen";
import TaskScreen from "./screens/TaskScreen/TaskScreen";
import OfficeScreen from "./screens/OfficeScreen/OfficeScreen";
import SettingsScreen from "./screens/SettingsScreen/SettingsScreen";
import { useAgentStore } from "./stores/agentStore";
import type { NavTab } from "./types";

function App() {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const fetchAgents = useAgentStore((s) => s.fetchAgents);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  function renderScreen() {
    switch (activeTab) {
      case "dashboard":
        return <Dashboard />;
      case "agents":
        return <AgentManager />;
      case "chat":
        return <ChatScreen />;
      case "tasks":
        return <TaskScreen />;
      case "office":
        return null; // Office is handled separately to preserve state
      case "settings":
        return <SettingsScreen />;
    }
  }

  return (
    <div className="app-shell">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="main-content">
        <div
          className={`office-screen-slot${activeTab === "office" ? " is-active" : ""}`}
          aria-hidden={activeTab !== "office"}
        >
          <OfficeScreen />
        </div>
        {renderScreen()}
      </main>
    </div>
  );
}

export default App;
