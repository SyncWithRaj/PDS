"""Shared prompt fragments to maintain DRY principles across LLM agents."""

SHARED_MERMAID_RULES = """
MERMAID DIAGRAM STYLING REQUIREMENTS (CRITICAL):
1. Node Labels: Each node MUST include a description using <br/> tag. YOU MUST USE QUOTES AROUND THE LABEL.
   GOOD: API_GW["API Gateway<br/>Rate limiting, TLS termination"]
   BAD:  API_GW["API Gateway"]
   BAD:  API_GW[API Gateway<br/>Rate limiting] (Missing quotes)
2. Edge Labels: MUST show the protocol AND data flowing.
   GOOD: API_GW -->|"REST/TLS 1.3 - Auth tokens"| AUTH_SVC
   BAD:  API_GW --> AUTH_SVC
3. DARK COLOR THEME - Add these exact classDef styles at the TOP of the flowchart:
   classDef client fill:#1a1a2e,stroke:#e94560,color:#ffffff,stroke-width:2px
   classDef ingress fill:#16213e,stroke:#0f3460,color:#ffffff,stroke-width:2px
   classDef compute fill:#0f3460,stroke:#533483,color:#ffffff,stroke-width:2px
   classDef eventbus fill:#1b1b2f,stroke:#1f4068,color:#e94560,stroke-width:2px
   classDef datastore fill:#162447,stroke:#e94560,color:#ffffff,stroke-width:2px
   classDef cache fill:#533483,stroke:#e94560,color:#ffffff,stroke-width:2px
   classDef ml fill:#1f4068,stroke:#533483,color:#ffffff,stroke-width:2px
   classDef infra fill:#0a0a23,stroke:#1f4068,color:#00d2ff,stroke-width:2px
4. Class Application: Apply the classes using the :::className syntax on each node.
   Example: WEB_CLIENT["Web/Mobile Client<br/>User interface"]:::client
5. Sequence diagram must be detailed and show exact payloads.
6. ASCII Only: No unicode characters. No special chars in labels without quotes.
"""

