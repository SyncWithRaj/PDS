# NirmanAI — Universal Cross-Domain Architecture Guide

> **How NirmanAI Dynamically Synthesizes Architectures for AI/ML, Autonomous Bots, Web, Mobile, IoT, and FinTech Systems**

---

## 1. Executive Summary

A common limitation of architectural generators is being hardcoded to standard CRUD web applications. **NirmanAI** is built from the ground up as a **universal architecture synthesis engine**. 

Through its **Domain Classification Engine** inside the Requirement Analyzer Agent, NirmanAI detects the exact software archetype from a natural language requirement and dynamically injects domain-specific design patterns, protocols, datastores, and specialized subsystems.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'darkMode': true, 'background': '#0b0f19', 'mainBkg': '#111827', 'lineColor': '#64748b' }}}%%
flowchart TD
    Prompt["User Requirement Prompt"] --> Analyzer["Requirement Analyzer Agent<br/>(Domain Classification Engine)"]

    Analyzer --> D1["1. Web & Mobile Applications<br/>(Social, E-Commerce, SaaS, Delivery)"]
    Analyzer --> D2["2. AI / ML & Data Platforms<br/>(RAG, RecSys, Vision, LLM Agents)"]
    Analyzer --> D3["3. Autonomous Bots & Crawlers<br/>(Trading, Discord/Telegram, Scrapers)"]
    Analyzer --> D4["4. Real-Time IoT & Streaming<br/>(Sensors, Telemetry, Live Gaming)"]
    Analyzer --> D5["5. FinTech & Transactional<br/>(Banking, Ledgers, Payment Gateways)"]

    classDef default fill:#1e293b,stroke:#475569,color:#f8fafc;
    classDef analyzer fill:#0c4a6e,stroke:#38bdf8,color:#f0f9ff,stroke-width:2px;
    classDef domain fill:#1e293b,stroke:#a855f7,color:#f8fafc,stroke-width:1px;

    class Prompt default;
    class Analyzer analyzer;
    class D1,D2,D3,D4,D5 domain;

    style D1 fill:#0b0f19,stroke:#0284c7,stroke-width:1px,color:#38bdf8;
    style D2 fill:#0b0f19,stroke:#db2777,stroke-width:1px,color:#f472b6;
    style D3 fill:#0b0f19,stroke:#7c3aed,stroke-width:1px,color:#c084fc;
    style D4 fill:#0b0f19,stroke:#d97706,stroke-width:1px,color:#fcd34d;
    style D5 fill:#0b0f19,stroke:#059669,stroke-width:1px,color:#34d399;
```

---

## 2. Domain Archetype Breakdown

| Software Category | Typical Use Cases | Specialized Subsystems & Technologies Injected |
| :--- | :--- | :--- |
| **AI / ML & LLM Systems** | Multimodal RAG, Recommendation engines, Computer vision pipelines, LLM agent workflows | • **Vector Databases**: Qdrant, Milvus, Pinecone<br/>• **Feature Stores**: Feast (Online Redis + Offline S3/Iceberg)<br/>• **Inference Servers**: vLLM, Triton with GPU dynamic batching<br/>• **Drift & MLOps**: Evidently AI, MLflow, ground truth collection |
| **Bots & Autonomous Agents** | High-frequency trading bots, Telegram/Discord agents, Distributed web scrapers | • **Event / Webhook Listeners**: Asynchronous event loop workers<br/>• **Task Queues & Workers**: Celery / Redis BullMQ for concurrent tasks<br/>• **Session Memory**: Redis key-value & vector memory for chat state<br/>• **Proxy & Rate Limit Pools**: Egress IP rotation & backoff strategies |
| **Mobile & Web Apps** | Social media, Food delivery, E-Commerce, Collaborative document editing | • **Ingress**: Global CDN (Cloudflare), API Gateway with OAuth2/JWT<br/>• **Push Notifications**: APNs (Apple) & FCM (Firebase)<br/>• **Real-Time Layer**: WebSockets / SSE for bidirectional communication<br/>• **Data Tier**: Sharded PostgreSQL/MongoDB + Redis Cache-Aside |
| **Real-Time IoT & Telemetry** | Fleet vehicle GPS tracking, Smart factory sensors, Live multiplayer gaming | • **Ingestion Protocols**: MQTT (EMQX), gRPC bi-directional streaming<br/>• **Stream Processing**: Apache Kafka + Apache Flink windowing<br/>• **Time-Series Storage**: TimescaleDB, InfluxDB, ClickHouse |
| **FinTech & High-Integrity** | Core banking ledgers, Crypto settlement, P2P payment wallets | • **Distributed Transactions**: SAGA pattern with compensating transactions<br/>• **Data Integrity**: Strict ACID guarantees, Raft consensus, zero eventual consistency<br/>• **Security**: Hardware Security Modules (HSM), PCI-DSS tokenization |

---

## 3. Side-by-Side Visual Comparison: AI Bot vs. Mobile App

The following diagram illustrates how the generated architecture changes drastically between an **AI / Bot system** and a **High-Scale Mobile App**:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'darkMode': true, 'background': '#0b0f19', 'mainBkg': '#111827', 'lineColor': '#64748b' }}}%%
graph TB
    subgraph Bot_Architecture ["Archetype A: AI Bot & Autonomous Agent System"]
        direction TB
        B_User["Discord / Telegram Webhook"] --> B_Worker["Async Task Worker<br/>(Celery / Redis Queue)"]
        B_Worker --> B_LLM["vLLM Inference Server<br/>(Quantized Open Model)"]
        B_Worker --> B_Vec["Qdrant Vector DB<br/>(RAG Knowledge Retrieval)"]
        B_Worker --> B_Mem["Redis Cache<br/>(Conversation Session Memory)"]
        B_Worker --> B_Proxy["Egress Proxy Pool<br/>(Rate Limit & IP Rotation)"]
    end

    subgraph Mobile_Architecture ["Archetype B: High-Concurrency Mobile App System"]
        direction TB
        M_Client["iOS / Android Mobile App"] --> M_CDN["Cloudflare Global CDN / WAF"]
        M_CDN --> M_GW["API Gateway (Envoy / Kong)<br/>• Rate Limiter & JWT Auth"]
        M_GW --> M_Service["User & Order Microservices (K8s)"]
        M_Service --> M_Push["APNs / FCM Push Gateway"]
        M_Service --> M_Cache["Redis Cluster (Cache-Aside)"]
        M_Service --> M_DB["PostgreSQL (Primary + Read Replicas)"]
    end

    classDef bot fill:#2e1065,stroke:#a855f7,color:#faf5ff,stroke-width:1px;
    classDef mobile fill:#082f49,stroke:#38bdf8,color:#f0f9ff,stroke-width:1px;

    class B_User,B_Worker,B_LLM,B_Vec,B_Mem,B_Proxy bot;
    class M_Client,M_CDN,M_GW,M_Service,M_Push,M_Cache,M_DB mobile;

    style Bot_Architecture fill:#0b0f19,stroke:#7c3aed,stroke-width:1px,color:#c084fc;
    style Mobile_Architecture fill:#0b0f19,stroke:#0284c7,stroke-width:1px,color:#38bdf8;
```

---

## 4. Deep Dive: The 5 Major Software Domains

### 4.1 AI / Machine Learning & Data Science Platforms

When an AI/ML prompt is provided (e.g., *"Build an AI-powered visual search engine for 50 million e-commerce images"*), NirmanAI automatically designs:
1. **Embedding Pipeline**: Offline image batch embedding ingestion into object storage (S3/MinIO) and index build in a Vector DB (**Qdrant / Milvus** with HNSW indexing).
2. **Feature Store**: Dual-tier storage using **Feast**:
   - *Online Store (Redis)*: Sub-5ms feature lookup for user embedding vectors.
   - *Offline Store (Apache Iceberg/S3)*: Parquet-formatted historical features for batch training.
3. **Inference Optimization**: **Triton Inference Server** with dynamic request batching, GPU memory paging, and TensorRT runtime.
4. **Continuous Feedback & Monitoring**: Ground truth capture into Kafka, evaluated by **Evidently AI** to trigger automated retraining upon feature/concept drift.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'darkMode': true, 'background': '#0b0f19', 'mainBkg': '#111827', 'lineColor': '#64748b' }}}%%
flowchart LR
    subgraph Data_Pipeline ["Data & Feature Engineering"]
        RAW["Raw Data Source"] --> FLINK["Apache Flink Stream"]
        FLINK --> ONLINE["Online Feature Store<br/>(Redis Cluster)"]
        FLINK --> OFFLINE["Offline Feature Store<br/>(Iceberg / Parquet)"]
    end

    subgraph Inference_Pipeline ["Low-Latency Model Inference"]
        REQ["Inference Request"] --> GW_ML["FastAPI Gateway"]
        GW_ML --> ONLINE
        GW_ML --> TRITON["Triton Inference Server<br/>(TensorRT GPU Cluster)"]
        GW_ML --> VEC["Qdrant Vector DB"]
    end

    subgraph Monitoring ["MLOps & Drift"]
        TRITON --> LOG["Prediction Stream (Kafka)"]
        LOG --> DRIFT["Drift Detector (Evidently AI)"]
        DRIFT -.->|Trigger Retrain| TRAIN["Kubeflow Training Job"]
    end

    classDef ml fill:#500724,stroke:#f472b6,color:#fdf2f8,stroke-width:1px;
    class RAW,FLINK,ONLINE,OFFLINE,REQ,GW_ML,TRITON,VEC,LOG,DRIFT,TRAIN ml;

    style Data_Pipeline fill:#0b0f19,stroke:#db2777,stroke-width:1px,color:#f472b6;
    style Inference_Pipeline fill:#0b0f19,stroke:#db2777,stroke-width:1px,color:#f472b6;
    style Monitoring fill:#0b0f19,stroke:#db2777,stroke-width:1px,color:#f472b6;
```

---

### 4.2 Autonomous Bots & Agentic Workflows

When the requirement specifies a bot or autonomous crawler (e.g., *"Build an automated arbitrage trading bot across decentralized exchanges"* or *"A multi-agent customer support bot"*):
1. **Event Ingestion**: Webhooks / long-polling listeners connected to message brokers with zero backpressure loss.
2. **Execution Workers**: Celery / Redis BullMQ workers executing asynchronous, non-blocking coroutines.
3. **Session State & Working Memory**: Redis key-value store maintaining short-term conversational context or active order book states.
4. **Anti-Blocking & Resilience**: Egress proxy pools with automatic circuit breakers and rotating user-agent headers.

---

### 4.3 High-Scale Mobile & Web Applications

For consumer-facing platforms (e.g., *"Ride-sharing app like Uber"* or *"Video sharing like TikTok"*):
1. **Client Edge**: Anycast DNS + CDN (Cloudflare/Fastly) caching static media and terminating TLS 1.3 near the user.
2. **Stateless Microservices**: Deployed on Kubernetes with Horizontal Pod Autoscaling (HPA) driven by CPU and custom request metrics.
3. **Push & Real-Time Sync**: WebSockets for live driver location and push gateways (APNs / FCM) for background notifications.
4. **Geo-Sharded Data Stores**: Relational databases partitioned by geographical region (e.g., `hash(city_id, user_id)`) to eliminate cross-region latency.

---

### 4.4 Real-Time IoT & Streaming Systems

For hardware, telemetry, and smart sensor fleets:
1. **Lightweight Protocols**: Ingestion via **MQTT** using high-throughput brokers like **EMQX** or **Mosquitto**.
2. **Stream Processing**: **Apache Kafka** partitioned by device UUID, consumed by **Apache Flink** for rolling-window anomaly detection.
3. **Time-Series Storage**: **TimescaleDB** or **ClickHouse** configured with data retention policies (e.g., 7 days raw data $\to$ 1 year rollups).

---

### 4.5 FinTech & High-Integrity Systems

For financial transactions, wallets, and double-entry ledgers:
1. **Strict ACID Guarantees**: Relational databases with serializable isolation levels and distributed consensus (**Raft**).
2. **Distributed SAGA Pattern**: Orchestration-based SAGA using Kafka topics with compensating transactions to avoid partial state failures.
3. **Idempotency & Deduplication**: Unique idempotency keys on every transaction request with Redis distributed locks.

---

## 5. Live Demonstration Scenarios (For PDS Presentations)

You can demonstrate NirmanAI's versatility live by executing these three vastly different prompts:

### Scenario 1: AI / Multimodal RAG System
> *"Design a medical AI diagnostic platform where doctors upload CT scans and patient histories to query diagnoses with sub-second vector search, HIPAA compliance, and model drift monitoring."*
* **Expected NirmanAI Output**: Qdrant Vector DB, Triton Inference Server, Feast Feature Store, S3 DICOM Object Store, and Evidently AI drift monitor.

### Scenario 2: Autonomous Trading Bot System
> *"Design a low-latency cryptocurrency arbitrage trading bot monitoring 10 exchanges with sub-millisecond price ingestion, automated order execution, risk circuit breakers, and crash recovery."*
* **Expected NirmanAI Output**: Asynchronous WebSocket worker pools, in-memory order books, Redis distributed locks, FIX protocol gateways, and dead-letter queues.

### Scenario 3: High-Scale Consumer Mobile App
> *"Design a food delivery mobile platform for 30 million users with live GPS courier tracking, restaurant menu search, order dispatching, and push notifications."*
* **Expected NirmanAI Output**: CDN + API Gateway, Kafka dispatch topic, Redis Geo-spatial index for driver matching, PostgreSQL sharded by city, and APNs/FCM push servers.

---

## 6. Summary

NirmanAI does **not** generate one-size-fits-all architectures. Its **Domain Classification Engine** ensures that every generated system design is purpose-built with the exact components, protocols, and data models required by that specific software domain.
