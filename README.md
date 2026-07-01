<p align="center">
  <img src="public/logo.jpg" alt="PerfectBlue Orchestrator Logo" width="160" style="border-radius: 50%;">
</p>

<p align="center">
  <h1 align="center">PerfectBlue Orchestrator</h1>
</p>

<p align="center">
  <a href="https://github.com/Platypus27-coder/perfect-blue-orchestrator/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/Platypus27-coder/perfect-blue-orchestrator?style=flat-square&color=3b82f6" alt="License">
  </a>
  <a href="https://github.com/Platypus27-coder/perfect-blue-orchestrator/issues">
    <img src="https://img.shields.io/github/issues/Platypus27-coder/perfect-blue-orchestrator?style=flat-square&color=8b5cf6" alt="Issues">
  </a>
  <a href="https://github.com/Platypus27-coder/perfect-blue-orchestrator/stargazers">
    <img src="https://img.shields.io/github/stars/Platypus27-coder/perfect-blue-orchestrator?style=flat-square&color=ec4899" alt="Stars">
  </a>
</p>

---

**PerfectBlue Orchestrator** is a bespoke, high-performance control dashboard for orchestrating and managing autonomous AI agents. It features a rich navy & blue-violet digital aesthetic, complete with a live 3D virtual office simulator (Claw3D) to visualize agent activities in real-time.

## Key Features

* **⚡ Control Center (Dashboard)**: Real-time agent status monitor, live activity stream, and core statistics indicators.
* **🤖 Agent Manager**: Configure, deploy, and manage up to 8 concurrent agents with custom roles (developer, researcher, designer, etc.) and model selection.
* **💬 Interactive Chat**: Direct messaging interface to prompt and interact with individual agents.
* **🏢 3D Office (Claw3D)**: Live iframe integration of the 3D virtual office visualizer with a custom Vietnam flag on the flagpole.
- **📦 Ultra-lightweight Architecture**: Decoupled from legacy code, built with React + Vite + Zustand.

## Tech Stack

- **Core**: React 19, TypeScript, Vite 8
- **State Management**: Zustand
- **Graphics**: Three.js, React Three Fiber
- **Icons**: Lucide React
- **Styling**: Modern CSS variables & tokens (`src/renderer/src/assets/main.css`)

## Getting Started

### 1. Run the Workspace
Launch both the Dashboard and the 3D Office concurrently using a single command:
```bash
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser. The 3D office scene on port `3000` will load automatically within the "Office" tab.
