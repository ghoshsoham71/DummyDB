# BurstDB - Synthesis Interface

This is the premium Next.js interface for the **BurstDB Synthesis System**. It provides a high-fidelity visual studio for schema modeling and a real-time **Synthesis Terminal** for cluster orchestration.

---

## 🛠️ UI Architecture

The interface is engineered for high-density information display and complex state management:

1.  **Framework**: Next.js 15+ (App Router) for optimized server-side rendering and client-side routing.
2.  **State Management**: **Zustand** orchestrates the global state machine, managing everything from active synthesis job polling to visual canvas blueprints.
3.  **Visualization Layer**:
    - **Recharts**: Low-latency rendering of fidelity distribution and privacy audit charts.
    - **Lucide**: Specialized technical iconography.
4.  **Motion Design**: Custom staggered entrance system powered by Tailwind CSS 4.0 animations (`animate-in-fade`, `animate-in-slide`).
5.  **Documentation**: Integrated **Nextra** documentation site for technical specifications.

---

## 🚀 Development Quick Start

### 1. Installation
```bash
npm install
```

### 2. Orchestration
Ensure the **API Gateway** (FastAPI) and **Redis Broker** are operational before booting the terminal.

```bash
npm run dev
```

The terminal will be available at [http://localhost:3000](http://localhost:3000).

---

## 📡 Terminal Views

The UI consolidates the entire post-generation workflow into a unified **Synthesis Terminal** featuring:
- **Infrastructure**: Cluster health and statistics.
- **Explorer**: High-speed synthetic data browsing.
- **Fidelity**: Statistical validation visualizations.

© 2024 BURSTDB SYNTHESIS SYSTEMS.
