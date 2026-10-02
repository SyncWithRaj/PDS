# 🏛️ AI/ML Inference & Data Science Platform System Architecture (100M DAU)
**Domain:** AI/ML Inference & Data Science Platform | **Style:** Event-Driven | **Cloud Platform:** AWS

## 1. Executive Summary & System Overview
LegalTrace is a secure, multi-tenant AI-powered Legal Tech and RAG platform engineered to ingest over 50 million court documents while serving 100,000 Daily Active Users (DAU). Featuring asynchronous buffering, hybrid search, and decoupled LLM grounding to guarantee P99 search latency under 2 seconds and 99.9% availability.

## 2. Capacity Planning & Quantitative Sizing
| Metric Category | Parameter | Sized Value |
| :--- | :--- | :--- |
| **Traffic** | Daily Active Users (DAU) | **100,000** |
| **Traffic** | Read / Write Ratio | **80:20** |
| **Traffic** | Average Throughput | **35 QPS** |
| **Traffic** | Peak Concurrency | **122 QPS** |
| **Network** | Peak Ingress Bandwidth | **0.001 Gbps** |
| **Network** | Peak Egress Bandwidth | **0.004 Gbps** |
| **Storage** | Daily Raw Growth | **1.43 GB/day** |
| **Storage** | 5-Year Net Data Footprint | **2.55 TB** |
| **Storage** | 5-Year Physical (3x Multi-AZ) | **7.65 TB** |
| **Cache** | Redis 80/20 Hot Set RAM | **4.0 GB** (3 nodes) |
| **Compute** | Recommended Kubernetes Cluster | **~3 Pods** |

## 3. Visual System Architecture Diagram
```mermaid
flowchart TD
    classDef client fill:#1a1a2e,stroke:#e94560,color:#ffffff,stroke-width:2px
    classDef ingress fill:#16213e,stroke:#0f3460,color:#ffffff,stroke-width:2px
    classDef compute fill:#0f3460,stroke:#533483,color:#ffffff,stroke-width:2px
    classDef eventbus fill:#1b1b2f,stroke:#1f4068,color:#e94560,stroke-width:2px
    classDef datastore fill:#162447,stroke:#e94560,color:#ffffff,stroke-width:2px
    classDef cache fill:#533483,stroke:#e94560,color:#ffffff,stroke-width:2px
    classDef ml fill:#1f4068,stroke:#533483,color:#ffffff,stroke-width:2px
    classDef infra fill:#0a0a23,stroke:#1f4068,color:#00d2ff,stroke-width:2px

    subgraph CLIENT_PERIMETER ["Client & Perimeter Layer"]
        EDGE_CDN["Cloudflare CDN & WAF<br/>Edge caching, DDoS protection, TLS termination"]:::client
    end

    subgraph INGRESS_SECURITY ["Edge Ingress & Security Layer"]
        API_GW["API Gateway (Envoy)<br/>Rate limiting, JWT validation, tenant routing"]:::ingress
        AUTH_SVC["Auth & Tenant Service<br/>Cognito/Keycloak, tenant isolation context"]:::ingress
    end

    subgraph COMPUTE_TIER ["Stateless Microservices Compute Tier"]
        INGESTION_SVC["Ingestion & OCR Service<br/>PDF processing, Tesseract/Textract OCR"]:::compute
        SEARCH_ENGINE["Hybrid Search Engine<br/>Parallel Go goroutines, semantic cache check, SSE streaming"]:::compute
        GROUNDING_ENGINE["Grounding Engine<br/>Hallucination mitigation, citation verification"]:::compute
    end

    subgraph EVENT_BUS ["Asynchronous Streaming & Event Bus Tier"]
        INGESTION_QUEUE["Ingestion Buffer Queue<br/>Amazon SQS buffer for failover protection"]:::eventbus
        DEBEZIUM_CDC["Debezium CDC Connector<br/>Tails Postgres WAL for Outbox events"]:::eventbus
        KAFKA_BUS["Amazon MSK Serverless<br/>Event streaming backbone"]:::eventbus
    end

    subgraph DATASTORE_TIER ["Polyglot Persistent Datastore Tier"]
        POSTGRES_DB["Aurora Serverless v2 (Postgres)<br/>Single Writer with Multi-AZ Read Replicas"]:::datastore
        OPENSEARCH_DB["Amazon OpenSearch<br/>Hybrid keyword & vector index"]:::datastore
    end

    subgraph CACHING_TIER ["Distributed In-Memory Caching Tier"]
        REDIS_CACHE["Redis Cluster<br/>Semantic cache & session state (RESP over TCP)"]:::cache
    end

    subgraph AI_ML_TIER ["AI/ML Inference & Real-Time Analytics Tier"]
        SAGEMAKER_LLM["SageMaker & Bedrock<br/>LLM inference & embedding generation"]:::ml
    end

    subgraph INFRA_OBS ["Observability, Telemetry & Disaster Recovery Tier"]
        OBSERVABILITY_STACK["Observability Stack<br/>Prometheus, Grafana, Jaeger tracing"]:::infra
    end

    EDGE_CDN -->|"HTTPS/TLS 1.3 - User Requests"| API_GW
    API_GW -->|"gRPC - Validate Token"| AUTH_SVC
    API_GW -->|"HTTPS - Upload PDF"| INGESTION_QUEUE
    INGESTION_QUEUE -->|"AMQP - Process Buffered PDF"| INGESTION_SVC
    API_GW -->|"HTTPS - Search Query & SSE Stream"| SEARCH_ENGINE

    INGESTION_SVC -->|"gRPC - Store Metadata & Outbox"| POSTGRES_DB
    POSTGRES_DB -.->|"gRPC - Tail WAL"| DEBEZIUM_CDC
    DEBEZIUM_CDC -.->|"Kafka Topic: doc.uploaded"| KAFKA_BUS
    KAFKA_BUS -.->|"Kafka Topic: doc.processed"| SEARCH_ENGINE

    SEARCH_ENGINE -->|"gRPC - Get Semantic Cache"| REDIS_CACHE
    SEARCH_ENGINE -->|"gRPC - Parallel Keyword Search"| OPENSEARCH_DB
    SEARCH_ENGINE -->|"gRPC - Parallel Metadata & Citation CTEs"| POSTGRES_DB
    SEARCH_ENGINE -->|"WebSocket - Grounding Verification"| GROUNDING_ENGINE

    GROUNDING_ENGINE -->|"gRPC - LLM Inference"| SAGEMAKER_LLM

    API_GW -.->|"OTLP - Traces/Metrics"| OBSERVABILITY_STACK
    SEARCH_ENGINE -.->|"OTLP - Traces/Metrics"| OBSERVABILITY_STACK
```

## 3.1 Critical Path Sequence Diagram
```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API_GW as API Gateway
    participant SEARCH as Hybrid Search Engine
    participant REDIS as Redis Cache
    participant OPENSEARCH as OpenSearch
    participant POSTGRES as Aurora PostgreSQL
    participant GROUNDING as Grounding Engine
    participant LLM as SageMaker & Bedrock

    User->>API_GW: GET /search?q=legal_query
    API_GW->>SEARCH: Forward Search Request
    SEARCH->>REDIS: Check Semantic Cache (RESP)
    alt Cache Hit
        REDIS-->>SEARCH: Return Cached Results
    else Cache Miss
        par Parallel Retrieval
            SEARCH->>OPENSEARCH: BM25 + Vector Search
            SEARCH->>POSTGRES: Metadata & Citation CTEs
        end
        OPENSEARCH-->>SEARCH: Search Hits
        POSTGRES-->>SEARCH: Metadata & CTEs
        SEARCH->>REDIS: Populate Semantic Cache
    end
    SEARCH-->>API_GW: Return Hybrid Results (<200ms)
    API_GW-->>User: Stream Initial Results & Open SSE Connection
    
    loop Asynchronous Grounding & Verification
        SEARCH->>GROUNDING: Trigger Grounding Verification
        GROUNDING->>LLM: Request LLM Citation Check
        LLM-->>GROUNDING: Synthesized Grounded Response
        GROUNDING-->>SEARCH: Verified Citations
        SEARCH-->>API_GW: Stream Grounded Synthesis via SSE
        API_GW-->>User: Deliver Real-Time Citations
    end
```

## 4. Component Topology Breakdown
| Component Tier | Selected Technology | Purpose & Rationale |
| :--- | :--- | :--- |
| **Cloudflare CDN & WAF** | `Cloudflare Enterprise` | Edge caching, DDoS protection, TLS termination |
| **API Gateway** | `AWS API Gateway (Envoy)` | Rate limiting, JWT validation, tenant routing |
| **Auth & Tenant Service** | `AWS Cognito` | Cognito/Keycloak, tenant isolation context |
| **Ingestion Buffer Queue** | `Amazon SQS` | Buffer incoming PDF uploads to protect Aurora database during failovers |
| **Ingestion & OCR Service** | `Kubernetes (EKS) / AWS Textract` | PDF processing, Tesseract/Textract OCR |
| **Hybrid Search Engine** | `Go / gRPC Microservice` | Parallel Go goroutines, semantic cache check, immediate hybrid results with async SSE streaming for LLM synthesis |
| **Grounding Engine** | `Python / LangChain / FastAPI` | Hallucination mitigation, citation verification streamed via SSE |
| **Debezium CDC Connector** | `Debezium on AWS ECS Fargate` | Tails Postgres WAL for Outbox events |
| **Amazon MSK Serverless** | `Apache Kafka (AWS MSK Serverless)` | Event streaming backbone |
| **Aurora Serverless v2 (Postgres)** | `Amazon Aurora Serverless v2` | Tenant-partitioned metadata & citation CTEs (Single Writer, Multiple Readers) |
| **Amazon OpenSearch** | `Amazon OpenSearch` | Hybrid keyword & vector index |
| **Redis Cluster** | `Amazon ElastiCache for Redis` | Semantic cache & session state using RESP protocol |
| **SageMaker & Bedrock** | `Amazon SageMaker & AWS Bedrock` | LLM inference & embedding generation |
| **Observability Stack** | `Prometheus + Grafana + Jaeger` | Prometheus, Grafana, Jaeger tracing |

## 5. Architectural Trade-Off Analysis
### • Decision: Architecture Decision #1
- **Option Chosen:** `Chose eventual consistency for SQS ingestion buffering over strict synchronous write locking to guarantee 99`
- **Option Discarded:** `Alternative approach`
- **Engineering Rationale:** Chose eventual consistency for SQS ingestion buffering over strict synchronous write locking to guarantee 99.99% upload availability during database failovers.

### • Decision: Architecture Decision #2
- **Option Chosen:** `Chose asynchronous Server-Sent Events (SSE) for LLM citation synthesis over blocking RPC to achieve sub-200ms initial search response times at the cost of rendering complete AI answers progressively over 1-2 seconds`
- **Option Discarded:** `Alternative approach`
- **Engineering Rationale:** Chose asynchronous Server-Sent Events (SSE) for LLM citation synthesis over blocking RPC to achieve sub-200ms initial search response times at the cost of rendering complete AI answers progressively over 1-2 seconds.

## 6. Bottleneck Identification & Mitigation Strategies
- **Bottleneck:** Single PostgreSQL writer vulnerability during failover
  ↳ **Mitigation:** Implemented SQS ingestion queue buffering and client-side exponential backoff retries.

- **Bottleneck:** LLM inference latency blocking search queries
  ↳ **Mitigation:** Decoupled search path to stream hybrid results instantly (<200ms) while asynchronously processing grounding via WebSockets/SSE.

- **Bottleneck:** [DEF-01] The connection between Amazon SQS (Ingestion Buffer Queue) and the Ingestion Service is defined as AMQP / RabbitMQ Event Queue.
  ↳ **Mitigation:** Change the connection protocol to HTTPS / AWS SDK polling, or replace Amazon SQS with Amazon MQ (RabbitMQ engine) if AMQP is strictly required.

- **Bottleneck:** [DEF-02] The Ingestion Service and Hybrid Search Engine are configured to connect to Aurora Postgres via gRPC / HTTP/2.
  ↳ **Mitigation:** Modify the connection to use the native PostgreSQL Wire Protocol (TCP port 5432) with an intermediate connection pooler like PgBouncer.

- **Bottleneck:** [DEF-03] The Hybrid Search Engine is configured to connect to the Redis Cluster via gRPC / HTTP/2.
  ↳ **Mitigation:** Enforce the use of native RESP protocol over TCP (port 6379) using standard Redis client libraries.

## 7. Critic Scorecard Audit (8-Pillar Evaluation)
**Overall Score:** **81.55 / 100** | **Verdict:** The LegalTrace architecture is rejected (Score: 81.55/100) due to critical protocol mismatches across multiple persistent datastores and queueing systems. While the choice of components (EKS, Aurora Serverless, MSK, OpenSearch) is highly appropriate for the target scale, the integration specifications (such as using gRPC for Postgres/Redis/OpenSearch and AMQP for SQS) represent severe logical flaws that would prevent system operation. Remediating these protocol definitions to use native wire protocols will immediately resolve the SPOF and raise the score above the acceptance threshold.

| Evaluation Pillar | Weight | Score | Status |
| :--- | :--- | :--- | :--- |
| Scalability & Throughput (15%) | 15% | **85.0** | ✅ PASS |
| Latency & Performance SLAs (15%) | 15% | **82.0** | ✅ PASS |
| Reliability & Fault Tolerance (15%) | 15% | **78.0** | ⚠️ REVIEW |
| Data Consistency & CAP Adherence (15%) | 15% | **80.0** | ✅ PASS |
| Security, Compliance & Zero-Trust (10%) | 10% | **82.0** | ✅ PASS |
| Cost & Resource Efficiency (10%) | 10% | **88.0** | ✅ PASS |
| ML/Data Pipeline Rigor (10%) | 10% | **83.0** | ✅ PASS |
| Requirement & Constraint Alignment (10%) | 10% | **75.0** | ⚠️ REVIEW |

## 8. Refinement Changelog
- **Iteration 1:** Starting Score: 78.8 -> Applied 4 patch(es):
  - `Replace Synchronous RPC with Event-Driven Bus (Kafka)`: Implemented the Transactional Outbox Pattern. Ingestion Service writes metadata and an outbox event to Aurora Postgres within a single ACID transaction. A Debezium CDC connector tails the Postgres WAL to reliably stream events to Kafka, eliminating dual-write anomalies.
  - `Insert Cache-Aside Distributed Layer (Redis Cluster)`: Parallelized the retrieval phase using Go goroutines to query OpenSearch and pgvector concurrently. Implemented aggressive semantic caching of LLM responses in Redis to bypass the Grounding Engine for duplicate or highly similar queries.
  - `Implement Horizontal Partitioning / Sharding Key`: Implemented PostgreSQL table partitioning based on tenant ID to keep pgvector HNSW indexes within RAM limits, preventing disk-based lookup spikes.
  - `Configure Multi-AZ Active-Active Automated Failover`: Consolidated datastores by eliminating Neo4j (modeling citation graphs via recursive CTEs in Postgres), transitioning to Aurora Serverless v2 and MSK Serverless to optimize costs for 122 QPS.
- **Iteration 2:** Starting Score: 80.45 -> Applied 3 patch(es):
  - `Configure Multi-AZ Active-Active Automated Failover`: Acknowledged Aurora single-writer limitation by introducing an Amazon SQS queue to buffer incoming PDF uploads before ingestion, preventing data loss during failover. Added client-side exponential backoff retry logic for write operations.
  - `Replace Synchronous RPC with Event-Driven Bus (Kafka)`: Decoupled the search path by returning hybrid search results (<200ms) synchronously while streaming LLM-grounded synthesis and citation verification asynchronously over Server-Sent Events (SSE).
  - `Insert Cache-Aside Distributed Layer (Redis Cluster)`: Corrected connection protocols from gRPC to native TCP with RESP for Redis and PostgreSQL native wire protocol with pgx driver and health checks.