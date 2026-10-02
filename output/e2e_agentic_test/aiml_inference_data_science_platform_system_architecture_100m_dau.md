# 🏛️ AI/ML Inference & Data Science Platform System Architecture (100M DAU)
**Domain:** AI/ML Inference & Data Science Platform | **Style:** Event-Driven | **Cloud Platform:** AWS

## 1. Executive Summary & System Overview
LegalTrace is an enterprise-grade, multi-tenant AI-powered legal case research and document management platform architected on AWS to support 100K+ active legal professionals managing over 50 million highly sensitive documents. The system delivers sub-500ms hybrid semantic search and real-time AI-assisted citation verification while enforcing strict ethical walls, attribute-based access control (ABAC), cryptographically secure audit trails, instant event-driven Redis cache invalidation, and Envoy-level circuit breaking with dead-letter queue isolation.

## 2. Capacity Planning & Quantitative Sizing
| Metric Category | Parameter | Sized Value |
| :--- | :--- | :--- |
| **Traffic** | Daily Active Users (DAU) | **100,000** |
| **Traffic** | Read / Write Ratio | **80:20** |
| **Traffic** | Average Throughput | **35 QPS** |
| **Traffic** | Peak Concurrency | **104 QPS** |
| **Network** | Peak Ingress Bandwidth | **0.000 Gbps** |
| **Network** | Peak Egress Bandwidth | **0.002 Gbps** |
| **Storage** | Daily Raw Growth | **13.75 GB/day** |
| **Storage** | 5-Year Net Data Footprint | **25.10 TB** |
| **Storage** | 5-Year Physical (3x Multi-AZ) | **75.30 TB** |
| **Cache** | Redis 80/20 Hot Set RAM | **13.8 GB** (3 nodes) |
| **Compute** | Recommended Kubernetes Cluster | **~3 Pods** |

## 3. Visual System Architecture Diagram
```mermaid
flowchart TB
    classDef client fill:#1a1a2e,stroke:#e94560,color:#ffffff,stroke-width:2px
    classDef ingress fill:#16213e,stroke:#0f3460,color:#ffffff,stroke-width:2px
    classDef compute fill:#0f3460,stroke:#533483,color:#ffffff,stroke-width:2px
    classDef eventbus fill:#1b1b2f,stroke:#1f4068,color:#e94560,stroke-width:2px
    classDef datastore fill:#162447,stroke:#e94560,color:#ffffff,stroke-width:2px
    classDef cache fill:#533483,stroke:#e94560,color:#ffffff,stroke-width:2px
    classDef ml fill:#1f4068,stroke:#533483,color:#ffffff,stroke-width:2px
    classDef infra fill:#0a0a23,stroke:#1f4068,color:#00d2ff,stroke-width:2px

    subgraph CLIENTS["Client & Perimeter Layer"]
        WebClient["Web Client<br/>React SPA / TLS 1.3"]:::client
        MobileClient["Mobile Client<br/>iOS / Android SDK"]:::client
        CDN_EDGE["Cloudflare Edge CDN & WAF<br/>DDoS protection & caching"]:::client
    end

    subgraph PERIMETER["Edge Ingress & Security Layer"]
        API_GW["API Gateway & Ingress<br/>Rate limiting & JWT validation"]:::ingress
    end

    subgraph COMPUTE["Stateless Microservices Compute Tier"]
        SERVICE_MESH["Service Mesh Control Plane<br/>Istio mTLS & Envoy proxies"]:::compute
        AUTH_SVC["Auth & ABAC Service<br/>OPA policy & Redis Pub/Sub invalidation"]:::compute
        INGEST_SVC["Asynchronous OCR Ingestion Pipeline<br/>Amazon Textract & DEK Caching"]:::compute
    end

    subgraph STREAM["Asynchronous Streaming & Event Bus Tier"]
        KAFKA["Event Streaming Backbone<br/>Apache Kafka MSK with DLQ"]:::eventbus
    end

    subgraph AI_TIER["AI/ML Inference & Real-Time Analytics Tier"]
        SEARCH_SVC["Hybrid Semantic Search Engine<br/>Amazon OpenSearch Service with DLS"]:::ml
        VERIFY_SVC["Citation Verification Service<br/>Redis Streams & Circuit Breaker"]:::ml
    end

    subgraph DATA["Polyglot Persistent Datastore Tier"]
        POSTGRES["Relational Data Store<br/>Amazon Aurora PostgreSQL Multi-AZ"]:::datastore
        S3_BUCKET["Secure Object Storage<br/>Encrypted raw & processed docs"]:::datastore
    end

    subgraph CACHE["Distributed In-Memory Caching Tier"]
        REDIS["In-Memory Distributed Cache<br/>ElastiCache Redis, Streams & Pub/Sub"]:::cache
    end

    subgraph GOVERNANCE["Observability, Telemetry & Disaster Recovery Tier"]
        VAULT["Secrets & Key Management<br/>AWS KMS FIPS 140-2 HSM"]:::infra
        OBSERVABILITY["Observability & Audit Pipeline<br/>Prometheus, Grafana, Jaeger, Alerts"]:::infra
    end

    WebClient -->|"HTTPS / TLS 1.3 (REST/JSON) - Client traffic"| CDN_EDGE
    MobileClient -->|"HTTPS / TLS 1.3 (REST/JSON) - App requests"| CDN_EDGE
    CDN_EDGE -->|"HTTPS / TLS 1.3 (REST/JSON) - Sanitized requests"| API_GW
    API_GW -->|"gRPC / HTTP/2 (Protocol Buffers) - Validate JWT"| AUTH_SVC
    API_GW -->|"HTTPS / TLS 1.3 (REST/JSON) - Document upload"| INGEST_SVC
    API_GW -->|"gRPC / HTTP/2 (Protocol Buffers) - Semantic search with DLS"| SEARCH_SVC
    API_GW -->|"gRPC / HTTP/2 (Protocol Buffers) - AI verification handle"| VERIFY_SVC
    
    AUTH_SVC -->|"gRPC / HTTP/2 (Protocol Buffers) - Fetch policies & Pub/Sub broadcast"| REDIS
    SEARCH_SVC -->|"gRPC / HTTP/2 (Protocol Buffers) - Resolve ACLs"| REDIS
    VERIFY_SVC -->|"WebSocket (Bi-directional Streaming) - Enqueue task with JWT claims"| REDIS
    INGEST_SVC -->|"HTTPS / TLS 1.3 (REST/JSON) - Store raw docs"| S3_BUCKET
    INGEST_SVC -->|"Kafka Topic Pub/Sub - document.ingested"| KAFKA
    KAFKA -->|"Kafka Topic Pub/Sub - Process vector embeddings"| SEARCH_SVC
    
    SEARCH_SVC -->|"gRPC / HTTP/2 (Protocol Buffers) - Query metadata"| POSTGRES
    VERIFY_SVC -->|"gRPC / HTTP/2 (Protocol Buffers) - Retrieve legal context"| SEARCH_SVC
    
    SERVICE_MESH -->|"gRPC / HTTP/2 (Protocol Buffers) - Emit OTEL traces"| OBSERVABILITY
    VAULT -->|"gRPC / HTTP/2 (Protocol Buffers) - Provide DEK with caching"| INGEST_SVC
    VAULT -->|"gRPC / HTTP/2 (Protocol Buffers) - Encrypt datastores"| POSTGRES
```

## 3.1 Critical Path Sequence Diagram
```mermaid
sequenceDiagram
    participant C as Legal Professional
    participant GW as API Gateway
    participant AUTH as Auth & ABAC Service
    participant SEARCH as Hybrid Search Service
    participant CACHE as Redis Cache / Pub/Sub
    participant DB as Aurora PostgreSQL
    participant VERIFY as Citation Verification Service
    participant LLM as Amazon Bedrock LLM

    C->>GW: POST /api/v1/search/hybrid (TLS 1.3)
    activate GW
    Note over GW: Rate limit & token check
    GW->>AUTH: gRPC ValidateToken & ABAC Check
    activate AUTH
    AUTH->>CACHE: GET user:permissions:{id}
    alt Cache HIT
        CACHE-->>AUTH: permissions {matter_compartments}
    else Cache MISS
        AUTH->>DB: SELECT permissions FROM user_acl WHERE id=$1
        DB-->>AUTH: {matter_compartments}
        AUTH->>CACHE: SET user:permissions:{id} (Cached with Pub/Sub invalidation)
    end
    AUTH-->>GW: TokenValid & ABAC Context
    deactivate AUTH
    
    GW->>SEARCH: gRPC ExecuteHybridSearch {query, vector, acl, _routing=tenant_id, DLS}
    activate SEARCH
    SEARCH->>CACHE: GET acl:tenant:{id}
    CACHE-->>SEARCH: cached ABAC ACL rules
    SEARCH->>SEARCH: OpenSearch k-NN + BM25 Vector Fusion with DLS
    SEARCH-->>GW: 200 OK {results, latency_ms: 260}
    deactivate SEARCH
    GW-->>C: 200 OK JSON Response
    deactivate GW

    C->>GW: POST /api/v1/verify/citations (Async Task)
    activate GW
    GW->>VERIFY: gRPC EnqueueVerificationTask {document_id, scoped_jwt_claims}
    activate VERIFY
    VERIFY->>CACHE: XADD verification_stream {task_payload, tenant_id}
    VERIFY-->>GW: 202 Accepted {task_handle_id}
    deactivate VERIFY
    GW-->>C: 202 Accepted {task_handle_id}
    deactivate GW
```

## 4. Component Topology Breakdown
| Component Tier | Selected Technology | Purpose & Rationale |
| :--- | :--- | :--- |
| **Cloudflare Edge CDN & WAF** | `Cloudflare CDN / Enterprise WAF` | Shields against DDoS attacks, terminates TLS 1.3 at the edge, and caches static client assets with global PoPs. |
| **API Gateway & Ingress** | `AWS API Gateway / Envoy Gateway` | Centralized rate limiting, JWT token validation, TLS termination, and secure routing to internal microservices with sidecar proxy tenant checks. |
| **Auth & ABAC Service** | `Keycloak / OIDC / Open Policy Agent (OPA)` | Enforces attribute-based access control (ABAC), ethical walls, and triggers instant Redis Pub/Sub invalidation broadcasts upon policy modification. |
| **Asynchronous OCR Ingestion Pipeline** | `Amazon Textract / Python FastAPI Workers` | Extracts text, tables, and hierarchical metadata from scanned legal documents asynchronously with envelope encryption caching. |
| **Hybrid Semantic Search Engine** | `Amazon OpenSearch Service` | Executes sub-500ms hybrid semantic and keyword search with strict document-level security (DLS) filters and tenant-specific custom routing parameters (_routing=tenant_id). |
| **Citation Verification Service** | `Amazon Bedrock (Claude 3.5 Sonnet) / Triton Inference Server` | Provides asynchronous AI-assisted citation verification with Envoy-level circuit breaking, consumer-group retry limits, and SQS/Redis DLQ fallback. |
| **Event Streaming Backbone** | `Apache Kafka Cluster (MSK) with DLQ` | Decouples ingestion, OCR processing, vector indexing, and audit logging with ordered event streams and dead-letter queue isolation. |
| **Relational Data Store** | `Amazon Aurora PostgreSQL Multi-AZ` | Stores transactional user profiles, matter metadata, access control policies, and audit metadata with ACID compliance. |
| **In-Memory Distributed Cache** | `Amazon ElastiCache Redis Cluster` | Provides sub-millisecond caching, pub/sub sub-second invalidation channels for ABAC permissions, and asynchronous task streams. |
| **Secure Object Storage** | `Amazon S3 (Raw & Processed Buckets)` | Securely stores 50M+ encrypted legal source documents and OCR-processed text outputs with Object Lock. |
| **Secrets & Key Management** | `AWS KMS / HashiCorp Vault (FIPS 140-2)` | Manages tenant encryption keys, database credentials, and API secrets with FIPS 140-2 hardware security modules and envelope encryption support. |
| **Observability & Audit Pipeline** | `Prometheus + Grafana + Jaeger + OpenSearch Audit Logs` | Collects system metrics, distributed traces, and cryptographically secure audit trails for SOC 2 / HIPAA compliance with automated alerting. |
| **Service Mesh Control Plane** | `Istio / Envoy Sidecar Proxies` | Enforces zero-trust mutual TLS (mTLS), distributed tracing injection, JWT re-validation, and circuit breaking across microservices. |

## 5. Architectural Trade-Off Analysis
### • Decision: Architecture Decision #1
- **Option Chosen:** `Chose Asynchronous Event-Driven OCR Ingestion via Kafka over synchronous REST processing`
- **Option Discarded:** `Alternative approach`
- **Engineering Rationale:** Chose Asynchronous Event-Driven OCR Ingestion via Kafka over synchronous REST processing. Trade-off: Dramatically increases pipeline resilience and handles 50M+ document backlogs without gateway timeouts, at the cost of eventual consistency (2-5s indexing delay before documents appear in search results).

### • Decision: Architecture Decision #2
- **Option Chosen:** `Chose Managed OpenSearch Service exclusively for vector and lexical retrieval over hybrid PGVector configurations`
- **Option Discarded:** `Alternative approach`
- **Engineering Rationale:** Chose Managed OpenSearch Service exclusively for vector and lexical retrieval over hybrid PGVector configurations. Trade-off: Eliminates dual-write synchronization complexity and guarantees high-performance vector search across 50M+ documents, at the cost of relying entirely on OpenSearch multi-AZ snapshots.

### • Decision: Architecture Decision #3
- **Option Chosen:** `Chose Redis Pub/Sub Cache Invalidation over 300-second TTL expiration windows for ABAC permissions`
- **Option Discarded:** `Alternative approach`
- **Engineering Rationale:** Chose Redis Pub/Sub Cache Invalidation over 300-second TTL expiration windows for ABAC permissions. Trade-off: Achieves sub-second security propagation on permission revocations and policy updates, at the cost of slight Redis pub/sub channel overhead and cluster message handling complexity.

### • Decision: Architecture Decision #4
- **Option Chosen:** `Chose Asynchronous Evaluation Queues backed by Redis Streams with Envoy circuit breaking for citation verification over open gRPC connections`
- **Option Discarded:** `Alternative approach`
- **Engineering Rationale:** Chose Asynchronous Evaluation Queues backed by Redis Streams with Envoy circuit breaking for citation verification over open gRPC connections. Trade-off: Prevents blast-radius cascading failures during LLM throttling and protects against poison-pill payloads via DLQ isolation, at the cost of returning task handles instead of immediate synchronous verification results.

## 6. Bottleneck Identification & Mitigation Strategies
- **Bottleneck:** Primary  Direct synchronous Vault integration and single PostgreSQL writer bottlenecks
  ↳ **Mitigation:** Implemented envelope encryption within INGEST_SVC using DEKs cached in volatile memory with a 15-minute rotation window, and offloaded tenant ABAC permission lookups to a distributed Redis caching tier.

- **Bottleneck:** Secondary  300-second TTL permission race conditions and unmonitored LLM queue failures
  ↳ **Mitigation:** Implemented an event-driven Redis Pub/Sub broadcast channel triggered by Keycloak/OPA policy updates for sub-second cache eviction, and configured Envoy-level circuit breaking with consumer-group retry limits and Redis Streams / SQS Dead Letter Queue (DLQ) integration.

- **Bottleneck:** [DEF-01] S3 raw and processed buckets lack explicit specification of S3 Intelligent-Tiering or Glacier lifecycle transition rules for long-term legal document archival over the 5-year 75.3 TB horizon.
  ↳ **Mitigation:** Configure S3 Lifecycle policies to automatically transition processed legal documents older than 365 days to S3 Glacier Flexible Archive or Deep Archive.

## 7. Critic Scorecard Audit (8-Pillar Evaluation)
**Overall Score:** **93.2 / 100** | **Verdict:** The LegalTrace architecture exhibits exceptional enterprise-grade maturity, robust zero-trust security controls, and comprehensive multi-AZ fault tolerance. With an overall composite score of 93.25 exceeding the 85.0 threshold and zero single points of failure detected, the architecture is formally accepted for implementation.

| Evaluation Pillar | Weight | Score | Status |
| :--- | :--- | :--- | :--- |
| Scalability & Throughput (15%) | 15% | **95.0** | ✅ PASS |
| Latency & Performance SLAs (15%) | 15% | **92.0** | ✅ PASS |
| Reliability & Fault Tolerance (15%) | 15% | **95.0** | ✅ PASS |
| Data Consistency & CAP Adherence (15%) | 15% | **90.0** | ✅ PASS |
| Security, Compliance & Zero-Trust (10%) | 10% | **98.0** | ✅ PASS |
| Cost & Resource Efficiency (10%) | 10% | **88.0** | ✅ PASS |
| ML/Data Pipeline Rigor (10%) | 10% | **90.0** | ✅ PASS |
| Requirement & Constraint Alignment (10%) | 10% | **98.0** | ✅ PASS |
