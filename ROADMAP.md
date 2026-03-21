# Mindora Infrastructure Roadmap

This document defines the **long-term infrastructure evolution plan** for the Mindora deployment.

The purpose of this project is **not application development**, but the systematic development of **production-grade infrastructure thinking** through incremental architectural evolution.

> "A complex system that works is invariably found to have evolved from a simple system that worked." — John Gall

Each version milestone represents a **meaningful infrastructure capability upgrade** — not a minor configuration change.

---

## Milestone Summary

| Version | Focus Area | Key Technology | Status |
|---|---|---|---|
| v1 | Baseline container deployment | Docker, Gunicorn, Cloudflare Tunnel | ✅ Complete |
| v2 | Reverse proxy architecture | Nginx | ✅ Complete |
| v3 | Infrastructure observability | Prometheus, Grafana, cAdvisor | 🔲 Planned |
| v4 | Deployment automation | GitHub Actions, CI/CD | 🔲 Planned |
| v5 | Persistent storage architecture | ZFS volumes, Docker mounts | 🔲 Planned |
| v6 | Security hardening | Network isolation, rate limiting | 🔲 Planned |
| v7 | Cloud deployment replication | VPS, Cloudflare DNS | 🔲 Planned |
| v8 | Infrastructure as Code | Provisioning scripts | 🔲 Planned |
| v9 | Advanced experiments | Orchestration, service mesh | 🔲 Planned |

---

## Current Architecture — v1 Baseline

**Architecture:**

```
User
 ↓
Cloudflare DNS + WAF
 ↓
Cloudflare Tunnel (CGNAT bypass)
 ↓
TrueNAS On-Prem Server
 ↓
Docker Runtime
 ↓
Flask Application Container (Gunicorn)
```

**Current capabilities:**

- On-premise deployment on TrueNAS SCALE
- ZFS storage with mirrored pool and snapshot scheduling
- Containerised application runtime with Docker Compose
- Secure inbound connectivity via Cloudflare Tunnel
- Container image registry via Docker Hub
- Environment variable–based secret management

**Current deployment pipeline:**

```
Local Machine → docker build → docker push → TrueNAS pull → docker compose up
```

Full architecture detail: [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## Version 2 — Reverse Proxy Architecture

**Objective:** Introduce a dedicated reverse proxy layer to separate traffic routing from application execution.

**Architecture change:**

```
[Before]  Cloudflare Tunnel → mindora container

[After]   Cloudflare Tunnel → Nginx container → mindora container
```

**What this enables:**

- Clean separation between routing logic and application logic
- Foundation for load balancing and multi-service routing in future versions
- Proper proxy header handling (`X-Forwarded-For`, `X-Real-IP`)
- Request buffering and timeout control at the edge of the stack

**Implementation tasks:**

- Add Nginx container to Compose stack
- Remove direct exposure of application container
- Route all HTTP traffic through Nginx
- Configure proxy headers, request timeouts, and buffer settings

**Deliverables:**

- `nginx.conf`
- Updated `docker-compose.yml`
- Updated `ARCHITECTURE.md`

---

## Version 3 — Infrastructure Observability

**Objective:** Introduce system visibility through metrics collection and dashboards. Running infrastructure without observability means operating blind.

**Architecture additions:**

```
Prometheus (metrics store)
    ├── Node Exporter     (host system metrics)
    └── cAdvisor          (container resource metrics)

Grafana (dashboards and visualisation)
```

**What this enables:**

- Real-time visibility into CPU, memory, disk IO, and network throughput
- Per-container resource consumption tracking
- Container restart event detection
- Foundation for alerting in future versions

**Dashboard targets:**

- Host CPU and memory utilisation
- Container restart frequency
- Disk IO per pool
- Network throughput

**Deliverables:**

- `prometheus.yml` configuration
- Grafana dashboard exports (JSON)
- Monitoring architecture documentation

---

## Version 4 — Deployment Automation

**Objective:** Replace the manual build and deploy process with a fully automated CI/CD pipeline.

**Current pipeline:**

```
Developer machine → docker build → docker push → NAS pull → container restart
```

**Target pipeline:**

```
git push → GitHub Actions → docker build → push to registry → SSH deploy → containers updated
```

**What this enables:**

- Every code change triggers a verified, consistent build
- No manual steps between code change and deployed state
- Deployment history and rollback capability via image tags

**Implementation tasks:**

- GitHub Actions workflow for Docker build and push
- Secure SSH-based deployment to TrueNAS host
- Automated container update trigger on new image push
- Optionally: automated rollback on health check failure

**Deliverables:**

- `.github/workflows/deploy.yml`
- SSH key configuration for deployment
- CI/CD documentation

---

## Version 5 — Persistent Storage Architecture

**Objective:** Separate application runtime state from the container lifecycle, enabling durable storage that survives container restarts and redeployments.

**Architecture change:**

```
[Before]  Application state lives inside the container (ephemeral)

[After]   Application Container
              ↓
          Mounted Docker volume
              ↓
          Dedicated ZFS dataset (apps/volumes/)
```

**What this enables:**

- Application data persists across container restarts and image updates
- Snapshot-based recovery for application state (databases, uploads)
- Clear separation between immutable application code and mutable data

**Implementation tasks:**

- Create dedicated ZFS datasets under `apps/volumes/`
- Mount volumes into the container via Compose
- Configure snapshot schedules on data volumes
- Validate data persistence across full container teardown and rebuild
- Define backup policy to `tank/backups/`

**Deliverables:**

- Updated `docker-compose.yml` with volume mounts
- ZFS dataset configuration
- Storage architecture documentation

---

## Version 6 — Infrastructure Security

**Objective:** Harden the infrastructure stack across network isolation, container runtime, and traffic filtering.

**What this enables:**

- Reduced attack surface across the container stack
- Network segmentation between services
- Rate limiting and request filtering at the proxy layer
- Principle of least privilege applied to container configuration

**Implementation tasks:**

- Isolate container networks (separate networks per service tier)
- Remove unnecessary container capabilities
- Configure Nginx rate limiting
- Audit and tighten Cloudflare WAF rules
- Restrict inter-container communication to required paths only
- Add container resource limits (CPU, memory)

**Deliverables:**

- Hardened `docker-compose.yml`
- Updated Nginx configuration with rate limiting
- Security architecture documentation

---

## Version 7 — Cloud Deployment Replication

**Objective:** Deploy the same architecture on a public cloud VPS to compare on-premises and cloud deployment characteristics.

**Architecture:**

```
Internet
 ↓
Cloudflare DNS
 ↓
VPS Public IP (firewall rules)
 ↓
Nginx Reverse Proxy
 ↓
Application Containers
```

**What this enables:**

- Direct comparison of on-prem vs cloud deployment
- Infrastructure portability validation — the same Compose stack deploys to both environments
- Experience with cloud-native networking and firewall configuration

**Implementation tasks:**

- Provision a VPS (DigitalOcean, Hetzner, or similar)
- Configure firewall rules (allow 80/443 only)
- Deploy the same container stack
- Document differences in setup, networking, and operational behaviour

**Deliverables:**

- Cloud deployment documentation
- On-prem vs cloud comparison analysis

---

## Version 8 — Infrastructure as Code

**Objective:** Convert manual infrastructure configuration steps into reproducible, version-controlled scripts.

**What this enables:**

- Full infrastructure can be reproduced from scratch automatically
- No undocumented manual steps
- Infrastructure state is auditable via version control

**Implementation tasks:**

- Document every manual setup step currently required
- Replace manual steps with provisioning scripts or IaC tooling
- Build and test a full reprovisioning workflow from a clean state

**Deliverables:**

- Provisioning scripts
- IaC configuration files
- Reprovisioning runbook

---

## Version 9 — Advanced Infrastructure Experiments

**Objective:** Explore distributed infrastructure patterns beyond single-node deployments.

These are learning-oriented experiments, not production deployments.

**Areas of exploration:**

- Container orchestration systems (Kubernetes, Nomad)
- Distributed service discovery
- Service mesh networking (mTLS, traffic policies)
- Large-scale observability pipelines
- Failure injection and chaos testing
- Multi-region failover architecture

---

## Development Principles

This project follows these infrastructure engineering principles:

- **Stability before complexity** — each version builds on a working foundation
- **Separation of concerns** — routing, application, storage, and monitoring are distinct layers
- **Observability as a requirement** — visibility is not optional
- **Automation over manual processes** — if it's done twice, it should be scripted
- **Documentation alongside implementation** — architecture docs are updated with every version

---

## Documentation Requirements

Every version milestone must update the following before being considered complete:

- [ ] `README.md` — project overview and component table
- [ ] `ARCHITECTURE.md` — updated diagrams and component descriptions
- [ ] `ROADMAP.md` — milestone status updated
- [ ] `CHANGELOG.md` — new version entry added

Each version must include:

- Architecture diagram reflecting the new state
- Explanation of what changed and why
- Any operational considerations introduced by the change

---

## Long-Term Goal

By the final stages, this repository should demonstrate:

- Real infrastructure deployment experience across on-prem and cloud environments
- Container networking and reverse proxy expertise
- Automated CI/CD deployment pipelines
- Monitoring and observability infrastructure
- Secure, hardened system design
- Reproducible infrastructure via code

The project is intended as a **public infrastructure case study** — demonstrating the progression from a minimal working system to a production-grade deployment architecture.