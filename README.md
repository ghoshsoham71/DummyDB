# BurstDB 

**BurstDB** is a state-of-the-art generative data synthesis platform designed for the modern, data-sovereign enterprise. It enables engineering teams to create high-fidelity, architecturally-aware synthetic databases for development, testing, and analytics without production data risk.

---

## 🏗️ Technical Architecture

BurstDB utilizes a distributed generation pipeline to ensure scalability and precision:

### 1. The Synthesis Protocol
BurstDB operates on a **Constraint-Aware Synthesis** model. Unlike simple random data generators, the platform utilizes a **ConstraintGraph** engine to parse and maintain referential integrity, unique constraints, and complex joint distributions across heterogeneous data sources.

### 2. Generative ML Layer
- **HMA (Hierarchical Multi-table Analysis)**: Specifically designed for deeply nested relational schemas. It captures recursive foreign key dependencies and preserves cross-table statistical correlations.
- **CTGAN (Conditional GAN)**: Utilized for high-entropy tabular data. It leverages conditional generators to handle imbalanced categorical columns and continuous data with non-Gaussian distributions.
- **Apache Arrow Integration**: All data interchange between the ML workers and the output buffers utilizes Apache Arrow (Feather/Parquet) for zero-copy serialized throughput.

### 3. Distributed Orchestration
- **Queueing Engine**: Redis-backed Celery clusters allow for horizontal scaling of synthesis nodes.
- **State Machine**: Powered by FastAPI and SQLAlchemy, managing complex job lifecycles from initial schema ingestion to final ZIP packaging.

---

## 🚀 Quick Start

### 1. Infrastructure Requirements
BurstDB requires **uv** for high-performance Python orchestration and **Node.js** for the premium interface.

```bash
# Clone the infrastructure
git clone https://github.com/ghoshsoham71/BurstDB.git
cd BurstDB
```

### 2. Backend Orchestration
```bash
cd api
uv sync
# Start the API Gateway (REST Interface)
uv run uvicorn main:app --reload
# Start the Synthesis Worker (Separate Terminal)
uv run celery -A src.celery_app worker --loglevel=info -P solo
```

### 3. Frontend Interface
```bash
cd ui
npm install
npm run dev
```

---

## 🔒 Security & Privacy (Differential Privacy)

BurstDB is engineered for **Data Sovereignty**:
- **Mathematical Guarantees**: Implements ε-differential privacy to ensure that synthetic outputs provide no statistical disclosure of individual production records.
- **Entity Identification (NER)**: Integrated PII discovery service that automatically masks and synthesizes sensitive markers during initial blueprinting.
- **Zero-Knowledge Architecture**: All synthesis happens strictly within your infrastructure; no data ever leaves the VPC.

---

## 🌐 Project Links

- [Documentation](http://localhost:3000/docs)
- [API Reference](http://localhost:8000/docs)
- [Architecture Specs](file:///c:/Users/KIIT/Desktop/DummyDB-1/ui/content/index.mdx)

