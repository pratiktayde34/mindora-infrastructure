# Changelog

All infrastructure changes to the Mindora deployment are documented here.

Each entry corresponds to a version milestone defined in [ROADMAP.md](./ROADMAP.md). The focus is on what changed architecturally and why — not a line-by-line diff.

---

## [v3.0.0] — Infrastructure Observability

**Status:** Complete

### What changed

Introduced a full observability stack — Prometheus, Grafana, Node Exporter, and cAdvisor — providing visibility into host system metrics and per-container resource consumption. All monitoring components run on `appnet` alongside the existing stack.

### Infrastructure introduced

- **Prometheus** — metrics store scraping all targets on a 15-second interval, 15-day retention, LAN accessible on port 9090
- **Grafana** — visualisation layer connected to Prometheus, LAN accessible on port 3000
- **Node Exporter** — host system metrics (CPU, memory, disk IO, network throughput, filesystem)
- **cAdvisor** — per-container resource metrics (CPU, memory, network per container)
- **prometheus_data** and **grafana_data** Docker volumes for persistent metric and dashboard storage

### Dashboards

| Dashboard | Grafana ID | Purpose |
|---|---|---|
| Node Exporter Quickstart | 13978 | Host system metrics |
| cAdvisor Exporter | 14282 | Per-container metrics |

### Key decisions

- Grafana and Prometheus kept LAN-only — internal infrastructure data should not be publicly accessible without authentication hardening planned for v6
- cAdvisor scrape interval set to 60s vs global 15s — cAdvisor observed at 166%+ CPU at 15s interval, container metrics don't require that granularity
- Node Exporter job renamed to `node` in prometheus.yml and instance relabeled to `truenas` for readable dashboard variable resolution
- Mindora app removed from scrape targets — Flask app has no `/metrics` endpoint, app-level instrumentation deferred

### What was intentionally deferred

CI/CD automation, persistent volume mounts, security hardening, Cloudflare Access for Grafana, and cloud deployment remain out of scope. Each is addressed in subsequent versions. See [ROADMAP.md](./ROADMAP.md).

---

## [v2.0.0] — Reverse Proxy Architecture

**Status:** Complete

### What changed

Introduced Nginx as a dedicated reverse proxy container sitting between the Cloudflare Tunnel connector and the application container. The Cloudflare Tunnel service URL was updated from `mindora:5000` to `nginx:80`.

### Infrastructure introduced

- **Nginx** reverse proxy container running `nginx:alpine` on the Docker bridge network
- **nginx.conf** — server block with proxy pass and proxy header configuration
- **`depends_on`** — Nginx waits for mindora to start before accepting traffic

### What changed in the stack

```
[Before]  cloudflared → mindora:5000

[After]   cloudflared → nginx:80 → mindora:5000
```

### Key architectural decision

Nginx introduces a routing layer that decouples the tunnel connector from the application. At single-service scale the immediate value is low — the real value compounds in v6 (rate limiting, security headers) and v7 (multi-service routing on VPS). The pattern is established now so those layers have somewhere to land.

Full reasoning documented in [ARCHITECTURE.md — Architectural Decisions](./ARCHITECTURE.md#architectural-decisions).

### What was intentionally deferred

Observability, CI/CD automation, persistent volume mounts, security hardening, and cloud deployment remain out of scope. Each is addressed in subsequent versions. See [ROADMAP.md](./ROADMAP.md).

---

## [v1.0.0] — Baseline Container Deployment

**Status:** Complete

### What was built

Established the foundational deployment architecture for the Mindora service on self-hosted on-premise infrastructure.

### Infrastructure introduced

- **TrueNAS SCALE** as the host platform — ZFS storage pools, container runtime, and system configuration management
- **ZFS mirror pool (`tank`)** across two HDDs for persistent data storage with single-disk failure tolerance
- **Dedicated SSD pool (`apps`)** for container workloads, isolated from persistent storage IO
- **ZFS snapshots** on datasets for point-in-time recovery
- **ZFS scrub schedule** for ongoing data integrity verification
- **SMART monitoring** on all storage devices for proactive disk health tracking
- **Docker + Gunicorn** containerised application deployment using a Python slim base image
- **Docker Compose** for declarative service orchestration replacing manual `docker run` commands
- **Docker Hub** as the container image registry
- **Cloudflare Tunnel** for secure public exposure without open router ports, bypassing CGNAT
- **Cloudflare DNS + WAF** for domain management, TLS termination, and edge filtering
- **TrueNAS configuration backup** exported to external cloud storage for full system rebuild capability

### Deployment pipeline established

```
Local build → Docker Hub → TrueNAS pull → docker compose up
```

### Key architectural decisions

- Cloudflare Tunnel chosen over VPS-based exposure to avoid managing an additional infrastructure node under CGNAT constraints
- Storage pools separated to prevent application IO contention with persistent data workloads
- Gunicorn chosen over Flask dev server for production-grade request handling
- Docker Compose chosen over `docker run` to keep infrastructure declared in version control

Full reasoning documented in [ARCHITECTURE.md — Architectural Decisions](./ARCHITECTURE.md#architectural-decisions).

### What was intentionally deferred

Reverse proxy, observability, CI/CD automation, persistent volume mounts, security hardening, and cloud deployment are all out of scope for this baseline. Each is addressed in subsequent versions. See [ROADMAP.md](./ROADMAP.md).

---

<!-- New entries added above this line, in reverse chronological order -->