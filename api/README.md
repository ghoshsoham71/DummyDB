# BurstDB - API Synthesis Gateway

The **BurstDB API** is a high-performance FastAPI service that orchestrates generative data synthesis tasks. It serves as the bridge between the UI and the distributed ML synthesis workers, utilizing a high-throughput **Apache Arrow** data plane.

---

## 🛠️ Internal Architecture

The API operates in an asynchronous task-driven model, specifically optimized for high-volume data serialization:

1.  **Gateway (FastAPI)**: Implements asynchronous handlers with Pydantic v2 validation. Manages REST routes for blueprint ingestion and cluster telemetry.
2.  **Constraint Engine**: Uses a proprietary **ConstraintGraph** logic to map SQL, NoSQL, and Graph schemas into a unified synthesis metadata format.
3.  **Task Broker (Redis)**: Orchestrates job distribution across the worker cluster using a priority-queued Celery architecture.
4.  **Worker Nodes (Celery)**: Dedicated compute units running the **ML Synthesis Layer**.
    - **Modeling**: SDV, CTGAN, and Gaussian Copula.
    - **Optimization**: All synthesis IO is handled via **Apache Arrow** for sub-second serialization of million-row datasets.

---

## 🚀 Orchestration Setup

### 1. Requirements
- **Python 3.13+** (using `uv` is strictly recommended for dependency resolution)
- **Redis 6.0+**
- **S3 / Local Storage** (for artifact buffering)

### 2. Installation & Sync
```bash
uv sync
```

### 3. Service Lifecycle

**Start the API Gateway**:
```bash
uv run uvicorn main:app --reload --port 8000
```

**Start the Distributed Workers**:
```bash
# Recommended: Run multiple workers for parallel synthesis
uv run celery -A src.celery_app worker --loglevel=info -P solo
```

---

## 📡 API Stratagem

### Blueprint Parsing
- `POST /parse`: Ingests SQL/DDL and reconstructs the architectural graph.
- `POST /parse/supabase`: Deep integration with Postgres reflection via SQLAlchemy.

### Synthesis Lifecycle
- `POST /synthetic/generate`: Dispatches a synthesis job with custom model parameters (scale, fidelity targets).
- `GET /synthetic/jobs/{id}/status`: Provides real-time progress percentages and cluster telemetry.
- `GET /synthetic/download/{id}`: Streams the generated Parquet/CSV archive.

---

## 📁 System Topology

- `main.py`: Service entry point and global exception orchestration.
- `src/celery_app.py`: Worker configuration and broker connection logic.
- `src/routers/`: Feature-sliced API routing (Synthesis, Blueprints, Jobs).
- `src/lib/ml`: Internal ML wrappers for SDV and data-cleaning protocols.

© 2024 BURSTDB SYNTHESIS SYSTEMS.