# Mindora Infrastructure — Architecture Documentation

**Version:** v3 — Infrastructure Observability  
**Last Updated:** 2025  
**Author:** Pratik Tayde

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
  - [Nginx Reverse Proxy](#nginx-reverse-proxy)
  - [Observability Stack](#observability-stack)
    - [Architecture](#architecture)
    - [Prometheus](#prometheus)
    - [Grafana](#grafana)
    - [Node Exporter](#node-exporter)
    - [cAdvisor](#cadvisor)
  - [Container Orchestration](#container-orchestration)
  - [Public Exposure via Cloudflare Tunnel](#public-exposure-via-cloudflare-tunnel)
  - [End-to-End Traffic Flow](#end-to-end-traffic-flow)
  - [Architecture Diagram](#architecture-diagram)
  - [Architectural Decisions](#architectural-decisions)
    - [Cloudflare Tunnel over VPS-based exposure](#cloudflare-tunnel-over-vps-based-exposure)
    - [Separate ZFS pools for `tank` and `apps`](#separate-zfs-pools-for-tank-and-apps)
    - [Gunicorn over Flask development server](#gunicorn-over-flask-development-server)
    - [Docker Compose over manual `docker run`](#docker-compose-over-manual-docker-run)
    - [Docker Hub over self-hosted registry](#docker-hub-over-self-hosted-registry)
    - [Nginx as a dedicated reverse proxy container](#nginx-as-a-dedicated-reverse-proxy-container)
    - [Grafana and Prometheus on LAN only](#grafana-and-prometheus-on-lan-only)
    - [Separate scrape intervals for cAdvisor](#separate-scrape-intervals-for-cadvisor)
  - [Current Limitations](#current-limitations)

---

## Overview

Mindora is a containerised Flask service running on a self-hosted TrueNAS SCALE node behind CGNAT. v3 introduces a full observability stack — Prometheus, Grafana, Node Exporter, and cAdvisor — providing visibility into host system metrics and per-container resource consumption.

The constraints that shaped this architecture are real: no public IP at the router level, on-premise hardware with independent failure domains, and a requirement for the system to be fully recoverable without manual reconstruction. Every architectural decision in this document traces back to one of those constraints.

**What changed in v3:** Prometheus, Grafana, Node Exporter, and cAdvisor were added to the existing stack on `appnet`. Prometheus scrapes Node Exporter for host metrics and cAdvisor for container metrics on a 15-second interval. Grafana is accessible on the LAN only via port 3000 — not exposed through the Cloudflare Tunnel. Prometheus is accessible on the LAN via port 9090 for debugging.

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

The application runs under Gunicorn inside a Python slim container. `expose` is used rather than `ports` — the container is intentionally not bound to the host network. All inbound traffic arrives from Nginx over the internal Docker network.

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

Build pipeline remains manual at v3. Each step is run locally — automated in v4.

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

## Nginx Reverse Proxy

Nginx runs as a dedicated container on the same Docker bridge network as the application. It receives all inbound requests from `cloudflared` and proxies them to the `mindora` container.

```nginx
server {
    listen 80;
    server_name mindora.pratiktayde.com;

    resolver 127.0.0.11 ipv6=off;

    location / {
        proxy_pass http://mindora:5000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Configuration file locations:

```
Repo:      infra/compose/nginx/nginx.conf
TrueNAS:   /mnt/apps/compose/mindora/nginx/nginx.conf
```

---

## Observability Stack

v3 introduces four new containers that form the observability layer. All run on `appnet` alongside the existing stack.

### Architecture

```
Node Exporter ──► 
                   Prometheus ──► Grafana ──► Operator
cAdvisor       ──►
```

Prometheus scrapes both exporters on a schedule. Grafana queries Prometheus on demand and renders dashboards.

### Prometheus

Time-series metrics store. Scrapes all targets on a 15-second interval and retains data for 15 days.

```
Port:      9090 (LAN accessible — bound to host)
Image:     prom/prometheus:latest
Storage:   prometheus_data Docker volume
Config:    ./prometheus/prometheus.yml
```

Scrape targets:

| Job | Target | Metrics |
|---|---|---|
| `prometheus` | `localhost:9090` | Prometheus self-metrics |
| `node` | `node_exporter:9100` | Host system metrics |
| `cadvisor` | `cadvisor:8080` | Per-container metrics |

The `node` job uses an instance relabel to replace `node_exporter:9100` with `truenas` for readable dashboard filtering.

Prometheus configuration:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ['localhost:9090']

  - job_name: node
    static_configs:
      - targets: ['node_exporter:9100']
        labels:
          instance: truenas

  - job_name: cadvisor
    scrape_interval: 60s
    static_configs:
      - targets: ['cadvisor:8080']
```

cAdvisor scrape interval is set to 60s rather than the global 15s — cAdvisor is resource intensive and per-container metrics don't require 15-second granularity.

### Grafana

Visualisation layer. Connects to Prometheus as a data source. Accessible on the LAN only — not exposed through the Cloudflare Tunnel.

```
Port:      3000 (LAN accessible — bound to host)
Image:     grafana/grafana:latest
Storage:   grafana_data Docker volume
Access:    http://192.168.1.x:3000
```

Dashboards imported from Grafana community library:

| Dashboard | ID | Purpose |
|---|---|---|
| Node Exporter Quickstart | 13978 | Host CPU, memory, disk, network |
| cAdvisor Exporter | 14282 | Per-container CPU, memory, network |

### Node Exporter

Exposes host system metrics — CPU, memory, disk IO, filesystem usage, network throughput. Runs with host PID namespace and mounts `/proc`, `/sys`, and `/` from the host to collect system-level data.

```
Port:      9100 (internal only — expose only)
Image:     prom/node-exporter:latest
```

### cAdvisor

Google's container advisor. Exposes per-container resource metrics by reading from the Docker socket and host filesystem. Runs privileged to access container runtime data.

```
Port:      8080 (internal only — expose only)
Image:     gcr.io/cadvisor/cadvisor:latest
```

---

## Container Orchestration

Seven containers share a single bridge network. All monitoring components are on `appnet` alongside the application stack.

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

  nginx:
    image: nginx:alpine
    container_name: nginx
    restart: unless-stopped
    expose:
      - "80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - mindora
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

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
    networks:
      - appnet

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    depends_on:
      - prometheus
    networks:
      - appnet

  node_exporter:
    image: prom/node-exporter:latest
    container_name: node_exporter
    restart: unless-stopped
    expose:
      - "9100"
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - appnet

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    expose:
      - "8080"
    privileged: true
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    networks:
      - appnet

networks:
  appnet:
    driver: bridge

volumes:
  prometheus_data:
  grafana_data:
```

Secrets are injected via `.env` at runtime — not stored in the Compose file or committed to version control.

---

## Public Exposure via Cloudflare Tunnel

The host operates behind CGNAT — no publicly routable IP exists at the router level, making inbound port forwarding impossible without an intermediary.

```
Tunnel name:   mindora-tunnel
Hostname:      mindora.pratiktayde.com
Service URL:   nginx:80
```

Grafana and Prometheus are intentionally not exposed through the tunnel — they contain internal infrastructure data and are accessible on the LAN only.

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
nginx container — reverse proxy :80
  ↓
mindora container — Gunicorn → Flask :5000

Monitoring (LAN only):
Node Exporter :9100 ──► Prometheus :9090 ──► Grafana :3000
cAdvisor :8080      ──►
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Public Internet                        │
│                                                             │
│   User ──► Cloudflare Edge (DNS + TLS + WAF)                │
└────────────────────────┬────────────────────────────────────┘
                         │ Cloudflare Tunnel
                         │ (outbound-initiated, no open ports)
┌────────────────────────▼────────────────────────────────────┐
│                  TrueNAS SCALE Host                         │
│                                                             │
│   ┌──────────────────────────────────────────────────┐      │
│   │              Docker Bridge (appnet)              │      │
│   │                                                  │      │
│   │  ┌─────────────┐  ┌──────────┐  ┌────────────┐   │      │
│   │  │ cloudflared │─►│  nginx   │─►│  mindora   │   │      │
│   │  │             │  │  :80     │  │  :5000     │   │      │
│   │  └─────────────┘  └──────────┘  └────────────┘   │      │
│   │                                                  │      │
│   │  ┌─────────────┐  ┌──────────┐                   │      │
│   │  │node_exporter│  │ cadvisor │                   │      │
│   │  │   :9100     │  │  :8080   │                   │      │
│   │  └──────┬──────┘  └────┬─────┘                   │      │
│   │         └──────┬───────┘                         │      │
│   │                ▼                                 │      │
│   │  ┌─────────────────────┐  ┌──────────────────┐   │      │
│   │  │  prometheus :9090   │─►│  grafana :3000   │   │      │
│   │  │  (LAN — port 9090)  │  │  (LAN — port 3000│   │      │
│   │  └─────────────────────┘  └──────────────────┘   │      │
│   └──────────────────────────────────────────────────┘      │
│                                                             │
│   ┌──────────────────┐  ┌──────────────────┐                │
│   │   tank (mirror)  │  │   apps (SSD)     │                │
│   │   HDD 1 + HDD 2  │  │   overlay2 + ZFS │                │
│   └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
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

### Nginx as a dedicated reverse proxy container

In v1, `cloudflared` routed directly to the `mindora` container. This works at single-service scale but couples routing logic to the application — adding a second service, rate limiting, or request filtering would require either modifying the app or adding Cloudflare-side rules.

Nginx introduces a clean seam between the tunnel connector and the application. Routing decisions, request buffering, proxy header injection, and future rate limiting all live in Nginx config without touching the application or the Cloudflare setup. As the stack grows — additional services in v7, rate limiting in v6 — Nginx is already in place to absorb those concerns.

---

### Grafana and Prometheus on LAN only

Exposing Grafana publicly through the Cloudflare Tunnel was considered. Both Grafana and Prometheus are kept LAN-only for two reasons.

First, they expose internal infrastructure data — host metrics, container resource consumption, and service names. This is information that should not be publicly accessible without authentication hardening that belongs in v6.

Second, Cloudflare Access could protect them but adds configuration complexity outside the scope of v3. LAN access via WARP is sufficient for operational use and keeps the scope of this version focused on getting metrics flowing rather than on access control.

---

### Separate scrape intervals for cAdvisor

cAdvisor scrapes the Docker runtime and container filesystem on every interval. At the global 15-second interval it consumes significant CPU — observed at 166-169% mean CPU usage across all cores. Container metrics don't require 15-second granularity for operational visibility.

cAdvisor is configured with a 60-second scrape interval while Node Exporter and Prometheus retain the 15-second global interval. Host metrics — CPU, memory, disk IO — benefit from higher resolution for detecting spikes. Container metrics are informational at this stage.

---

## Current Limitations

The following are known gaps, each with a planned resolution:

| Limitation | Planned Resolution |
|---|---|
| No CI/CD pipeline | v4 — GitHub Actions |
| No persistent volume mounts | v5 — Storage Architecture |
| No container privilege hardening | v6 — Security |
| No container health checks | v6 — Security |
| No resource limits on containers | v6 — Security |
| Grafana and Prometheus not publicly accessible | v6 — Security (Cloudflare Access) |
| No cloud deployment | v7 — Cloud Replication |
| No infrastructure as code | v8 — IaC |

See [ROADMAP.md](./ROADMAP.md) for full detail on each milestone.