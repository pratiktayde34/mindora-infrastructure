# Mindora Infrastructure — Architecture Documentation

**Version:** v1 — Baseline Container Deployment  

---

## Table of Contents

- [Mindora Infrastructure — Architecture Documentation](#mindora-infrastructure--architecture-documentation)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Hardware Layout](#hardware-layout)
  - [Storage Architecture](#storage-architecture)
    - [Data Pool — `tank`](#data-pool--tank)
    - [Applications Pool — `apps`](#applications-pool--apps)
  - [Data Integrity and Reliability](#data-integrity-and-reliability)
    - [ZFS Snapshots](#zfs-snapshots)
    - [ZFS Scrub Schedule](#zfs-scrub-schedule)
    - [SMART Monitoring](#smart-monitoring)
  - [Recovery and Rebuild Strategy](#recovery-and-rebuild-strategy)
    - [TrueNAS Configuration Backup](#truenas-configuration-backup)
    - [Application Data Replication](#application-data-replication)
  - [Container Runtime Environment](#container-runtime-environment)
  - [Domain and DNS Configuration](#domain-and-dns-configuration)
  - [Application Containerisation](#application-containerisation)
  - [Container Build and Distribution](#container-build-and-distribution)
  - [Container Orchestration](#container-orchestration)
  - [Public Exposure via Cloudflare Tunnel](#public-exposure-via-cloudflare-tunnel)
  - [End-to-End Traffic Flow](#end-to-end-traffic-flow)
  - [Baseline Architecture Diagram](#baseline-architecture-diagram)
  - [Architectural Decisions](#architectural-decisions)
    - [Cloudflare Tunnel over VPS-based exposure](#cloudflare-tunnel-over-vps-based-exposure)
    - [Separate ZFS pools for `tank` and `apps`](#separate-zfs-pools-for-tank-and-apps)
    - [Gunicorn over Flask development server](#gunicorn-over-flask-development-server)
    - [Docker Compose over manual `docker run`](#docker-compose-over-manual-docker-run)
    - [Docker Hub over self-hosted registry](#docker-hub-over-self-hosted-registry)
  - [Current Limitations](#current-limitations)

---

## Overview

Mindora is a containerised Flask service running on a self-hosted TrueNAS SCALE node behind CGNAT. The deployment is intentionally minimal — v1 exists to establish a stable, reproducible foundation before introducing additional infrastructure layers.

The constraints that shaped this architecture are real: no public IP at the router level, on-premise hardware with independent failure domains, and a requirement for the system to be fully recoverable without manual reconstruction. Every architectural decision in this document traces back to one of those constraints.

Future iterations are documented in [ROADMAP.md](./ROADMAP.md).

---

## Hardware Layout

Three devices, three distinct roles — OS, persistent storage, and application workloads are separated to eliminate IO contention and create independent failure domains.

```
TrueNAS Host
│
├── Boot Device
│   └── SSD — TrueNAS OS
│
├── Data Pool (tank)
│   ├── HDD 1 ─┐
│   └── HDD 2 ─┴─ ZFS mirror
│
└── Applications Pool (apps)
    └── SSD — container workloads
```

| Device | Pool | Workload |
|---|---|---|
| Boot SSD | — | TrueNAS OS only |
| HDD 1 + HDD 2 | `tank` | Persistent data, SMB shares, backups |
| Apps SSD | `apps` | Container images, volumes, runtime state |

The separation between `tank` and `apps` is a deliberate design choice — covered in [Architectural Decisions](#architectural-decisions).

---

## Storage Architecture

### Data Pool — `tank`

ZFS mirror across two HDDs. Tolerates single-disk failure with no service interruption.

```
tank/
├── smb-share-1
├── smb-share-2
└── backups/
```

`tank` is the durability layer. Application runtime data is periodically replicated here from the SSD pool.

### Applications Pool — `apps`

Dedicated SSD-backed ZFS pool for container workloads.

```
apps/
├── compose/    ← orchestration definitions
└── volumes/    ← persistent runtime state
```

The SSD backing provides the IO throughput container workloads require, while ZFS gives the same integrity guarantees as the HDD pool — checksumming, snapshot capability, and scrub support.

---

## Data Integrity and Reliability

### ZFS Snapshots

Periodic snapshots are scheduled on datasets. The primary use case is recovery from application-layer mistakes — bad deploys, accidental data deletion, configuration errors — rather than hardware failure, which the mirror handles.

Retention policies are configured per dataset based on how frequently the data changes and how far back recovery needs to be possible.

### ZFS Scrub Schedule

Regular scrubs run across both pools. On the mirrored `tank` pool, any checksum mismatch triggers automatic correction from the redundant copy. The scrub schedule is the early warning system for latent disk degradation before it becomes data loss.

### SMART Monitoring

Short and extended SMART tests are scheduled on all drives. The goal is detecting early degradation indicators — reallocated sectors, pending sectors, read error rates — with enough lead time to order a replacement before failure.

| Test | Schedule |
|---|---|
| Short | Frequent — quick health check |
| Extended | Periodic — full surface scan |

---

## Recovery and Rebuild Strategy

The system is designed around a single principle: recovery should require no manual reconstruction from memory.

### TrueNAS Configuration Backup

TrueNAS configuration exports include pool definitions, dataset structure, network config, users, permissions, and container runtime state. These are stored in external cloud storage.

**Boot SSD failure recovery:**

```
1. Install TrueNAS on replacement drive
2. Import existing ZFS pools — data is intact on the disks
3. Restore configuration backup
```

The ZFS pools survive independently of the OS drive. The configuration backup restores everything else.

### Application Data Replication

```
apps/volumes/  →  replicated to  →  tank/backups/
(SSD — runtime performance)         (HDD mirror — durability)
```

SSD failure does not affect `tank`. Application data is restored from the HDD-backed replica and the stack is redeployed from the same image on Docker Hub.

---

## Container Runtime Environment

TrueNAS SCALE runs a Docker-compatible runtime. When `apps` is assigned as the application pool, TrueNAS provisions `/mnt/.ix-apps` on that dataset for container images, layers, and metadata.

```
Storage driver:       overlay2
Backing filesystem:   ZFS
```

Container storage inherits ZFS checksumming — silent corruption in image layers is detectable at the storage level.

---

## Domain and DNS Configuration

Domain `pratiktayde.com` is registered through Cloudflare Registrar. All DNS is managed through Cloudflare, keeping edge services — WAF, tunnel routing, CDN — consolidated under one control plane.

| Service | Role in this architecture |
|---|---|
| DNS | Resolution and subdomain routing |
| WAF | Edge-level request filtering |
| Tunnel | Inbound ingress without open router ports |

Public endpoint: `mindora.pratiktayde.com`

---

## Application Containerisation

The application runs under Gunicorn inside a Python slim container. Worth noting: `expose` is used rather than `ports` — the container is intentionally not bound to the host network. All inbound traffic arrives through the tunnel connector on the internal Docker network.

```dockerfile
FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
```

---

## Container Build and Distribution

Build pipeline at v1 is manual. Each step is run locally — automated in v4.

```bash
# Build and validate locally before pushing
docker build -t mindora:test .
docker run -p 5000:5000 mindora:test

# Tag and distribute
docker tag mindora:test pratiktayde/mindora:test
docker push pratiktayde/mindora:test

# Deploy on TrueNAS
docker pull pratiktayde/mindora:test
docker compose up -d
```

Registry: `pratiktayde/mindora` on Docker Hub.

---

## Container Orchestration

Both containers share a single bridge network — `cloudflared` reaches `mindora` by container name via Docker DNS over that network.

```
Repo:      infra/compose/docker-compose.prod.yml
TrueNAS:   /mnt/apps/compose/mindora/
```

```yaml
services:
  mindora:
    image: pratiktayde/mindora:test
    container_name: mindora
    restart: unless-stopped
    expose:
      - "5000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    networks:
      - appnet

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${TUNNEL_TOKEN}
    networks:
      - appnet

networks:
  appnet:
    driver: bridge
```

Secrets are injected via `.env` at runtime — not stored in the Compose file or committed to version control.

---

## Public Exposure via Cloudflare Tunnel

The host operates behind CGNAT — no publicly routable IP exists at the router level, making inbound port forwarding impossible without an intermediary.

The tunnel connector runs as a container on the same bridge network as the application. It establishes an outbound connection to Cloudflare's edge, which Cloudflare uses to route inbound requests back to the service. The router has no open ports.

```
Tunnel name:   mindora-tunnel
Hostname:      mindora.pratiktayde.com
Service URL:   mindora:5000
```

`cloudflared` resolves `mindora` by Docker DNS — both containers on `appnet`, container name as the upstream service URL.

---

## End-to-End Traffic Flow

```
User
  ↓
Cloudflare Edge — DNS resolution, TLS termination, WAF
  ↓
Cloudflare Tunnel — encrypted, outbound-initiated
  ↓
cloudflared container
  ↓
Docker bridge network (appnet)
  ↓
mindora container — Gunicorn → Flask :5000
```

TLS terminates at Cloudflare. Traffic between `cloudflared` and `mindora` is internal to the Docker bridge — HTTP only, never exposed outside the host.

---

## Baseline Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   Public Internet                   │
│                                                     │
│   User ──► Cloudflare Edge (DNS + TLS + WAF)        │
└────────────────────────┬────────────────────────────┘
                         │ Cloudflare Tunnel
                         │ (outbound-initiated, no open ports)
┌────────────────────────▼────────────────────────────┐
│               TrueNAS SCALE Host                    │
│                                                     │
│   ┌─────────────────────────────────────────┐       │
│   │         Docker Bridge (appnet)          │       │
│   │                                         │       │
│   │  ┌──────────────┐  ┌─────────────────┐  │       │
│   │  │  cloudflared │─►│    mindora      │  │       │
│   │  │              │  │  Gunicorn :5000 │  │       │
│   │  └──────────────┘  └─────────────────┘  │       │
│   └─────────────────────────────────────────┘       │
│                                                     │
│   ┌──────────────────┐  ┌──────────────────┐        │
│   │   tank (mirror)  │  │   apps (SSD)     │        │
│   │   HDD 1 + HDD 2  │  │   overlay2 + ZFS │        │
│   └──────────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────┘
```

---

## Architectural Decisions

### Cloudflare Tunnel over VPS-based exposure

The server operates behind CGNAT — the ISP assigns a single public IP shared across multiple customers, making traditional inbound port forwarding impossible at the router level.

The obvious workaround is a VPS with a public IP acting as a reverse proxy or jump host. Cloudflare Tunnel was chosen instead because it solves the ingress problem without introducing a separate node to operate. The `cloudflared` container maintains the outbound connection to Cloudflare's edge; Cloudflare handles the public-facing side. No additional infrastructure, no additional failure point.

The trade-off is a hard dependency on Cloudflare for all inbound traffic — if Cloudflare is down, the service is unreachable regardless of host health. That's an acceptable trade at this scale given what comes included: TLS termination, WAF, DDoS mitigation, and DNS under one control plane. A direct VPS deployment is planned for v7 specifically to compare both approaches with real operational experience behind each.

---

### Separate ZFS pools for `tank` and `apps`

A single pool could host both workloads. The separation exists for two reasons.

First, IO isolation. Container workloads are bursty — image pulls, overlay operations, and application IO can all spike simultaneously. Colocating that on the same pool as long-term storage creates contention and makes per-pool health harder to reason about independently.

Second, failure domain separation. A failing HDD in the `tank` mirror has zero impact on application availability — the `apps` SSD continues operating. Conversely, an SSD failure takes down the container runtime but leaves persistent data on `tank` completely intact. Recovery is clean and scoped: rebuild the apps pool, restore from backup, redeploy.

---

### Gunicorn over Flask development server

The Flask dev server is single-process and explicitly documented as unsafe for production. Gunicorn was the only reasonable choice for a containerised deployment — multi-worker process model, proper signal handling, and request queuing without blocking. It's a single line change in the Dockerfile with a meaningful operational difference in how the process behaves under concurrent load and on worker failure.

---

### Docker Compose over manual `docker run`

The initial deployment used `docker run` directly. The problem is that the infrastructure state lives in shell history rather than version control. Compose defines the full service configuration — image, environment, network membership, restart policy — in a file that is reproducible exactly on any host. As the stack grows across versions, every new service gets the same treatment automatically.

---

### Docker Hub over self-hosted registry

Running a registry on the NAS was considered. Docker Hub was chosen at this stage because operating a registry adds a service to maintain, monitor, and back up — scope not justified when the goal is establishing a clean build-and-deploy pipeline. This gets revisited if the CI/CD pipeline in v4 hits pull rate limits or if a private registry becomes a security requirement.

---

## Current Limitations

This baseline is intentionally minimal. The following are known gaps, each with a planned resolution:

| Limitation | Planned Resolution |
|---|---|
| No reverse proxy layer | v2 — Nginx |
| No metrics or dashboards | v3 — Prometheus + Grafana |
| No CI/CD pipeline | v4 — GitHub Actions |
| No persistent volume mounts | v5 — Storage Architecture |
| No container privilege hardening | v6 — Security |
| No container health checks | v6 — Security |
| No resource limits on containers | v6 — Security |
| No cloud deployment | v7 — Cloud Replication |
| No infrastructure as code | v8 — IaC |

See [ROADMAP.md](./ROADMAP.md) for full detail on each milestone.
