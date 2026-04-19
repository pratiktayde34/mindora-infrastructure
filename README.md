# Mindora Infrastructure

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Version](https://img.shields.io/badge/version-v3--observability-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Infrastructure architecture and deployment configuration for the Mindora application.

This repository documents the containerized deployment, networking architecture, and on-premise infrastructure used to run the Mindora service. The system is currently deployed on a self-hosted TrueNAS server and exposed securely to the internet using Cloudflare Tunnel.

> **Focus:** This repository is about **infrastructure architecture**, not application development. The Flask app is the workload — the infrastructure is the subject.

---

## Table of Contents

- [Mindora Infrastructure](#mindora-infrastructure)
  - [Table of Contents](#table-of-contents)
  - [Quick Links](#quick-links)
  - [Project Overview](#project-overview)
  - [Architecture Overview](#architecture-overview)
  - [Infrastructure Components](#infrastructure-components)
    - [Application Container](#application-container)
    - [Docker Compose Deployment](#docker-compose-deployment)
    - [Cloudflare Tunnel](#cloudflare-tunnel)
    - [On-Premise Infrastructure](#on-premise-infrastructure)
  - [Repository Structure](#repository-structure)
  - [Prerequisites](#prerequisites)
  - [Deployment Strategy](#deployment-strategy)
  - [Roadmap](#roadmap)
  - [Goals of This Repository](#goals-of-this-repository)
  - [License](#license)

---

## Quick Links

- 🌐 **Live Deployment:** [mindora.pratiktayde.com](https://mindora.pratiktayde.com)
- 🏗 **Architecture Documentation:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- 🗺 **Infrastructure Roadmap:** [ROADMAP.md](./ROADMAP.md)
- 📋 **Changelog:** [CHANGELOG.md](./CHANGELOG.md)

---

## Project Overview

Mindora is a Flask-based web application deployed using a production-oriented containerized infrastructure stack.

Key characteristics of the system:

- Containerized application deployment using Docker and Gunicorn
- Infrastructure orchestration using Docker Compose
- Secure internet exposure using Cloudflare Tunnel (CGNAT bypass)
- On-premise hosting using TrueNAS SCALE
- Resilient ZFS storage with mirrored pools and snapshot scheduling
- System configuration backups for rapid rebuild capability
- Disk health monitoring via SMART tests
- Periodic ZFS scrub tasks for data integrity verification

---

## Architecture Overview

```
User
 ↓
Cloudflare Edge (DNS + TLS + WAF)
 ↓
Cloudflare Tunnel
 ↓
On-Premise TrueNAS Server
 ↓
Docker Bridge Network
 ↓
Nginx Reverse Proxy
 ↓
Flask Application Container (Gunicorn)
```

Cloudflare handles TLS termination and edge routing. The application remains entirely within the private network — no ports are exposed on the router.

Full architecture documentation: [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## Infrastructure Components

### Application Container

The Flask application runs inside a Docker container built from a Python slim base image, served by Gunicorn. It is not directly exposed to the public internet — all traffic arrives through the Cloudflare Tunnel connector.

Internal port: `5000`

---

### Docker Compose Deployment

The compose stack currently includes:

- **mindora** — Flask application container (Gunicorn)
- **nginx** — Reverse proxy container
- **cloudflared** — Cloudflare Tunnel connector
- **prometheus** — Metrics store (LAN :9090)
- **grafana** — Dashboards (LAN :3000)
- **node_exporter** — Host system metrics
- **cadvisor** — Per-container metrics
- **appnet** — Internal Docker bridge network

Compose configuration (repo):

```
infra/compose/docker-compose.prod.yml
```

Deployed location on TrueNAS:

```
/mnt/apps/compose/mindora/
```

---

### Cloudflare Tunnel

Because the server operates behind CGNAT, inbound port forwarding is not possible. Cloudflare Tunnel establishes an outbound encrypted connection from the server to Cloudflare's edge — enabling secure public access without exposing the internal network.

Public endpoint: [https://mindora.pratiktayde.com](https://mindora.pratiktayde.com)

---

### On-Premise Infrastructure

The system runs on a dedicated TrueNAS SCALE server with:

| Feature | Detail |
|---|---|
| OS pool | Dedicated boot SSD |
| Data pool (`tank`) | ZFS mirror across 2 HDDs |
| Apps pool (`apps`) | Dedicated SSD |
| Snapshots | Periodic, per-dataset |
| Scrub schedule | Regular integrity verification |
| SMART monitoring | Short + extended tests scheduled |
| Config backup | Exported to cloud storage |

---

## Repository Structure

```
mindora-infrastructure/
│
├── app/                          # Flask application source
│
├── infra/
│   ├── docker/
│   │   └── Dockerfile            # Container build definition
│   └── compose/
│       ├── docker-compose.prod.yml
│       ├── nginx/
│       │   └── nginx.conf        # Nginx reverse proxy configuration
│       └── prometheus/
│           └── prometheus.yml    # Prometheus scrape configuration
│
├── README.md                     # Project overview (this file)
├── ARCHITECTURE.md               # Full infrastructure architecture
├── ROADMAP.md                    # Planned infrastructure milestones
├── CHANGELOG.md                  # Version history and architectural changes
└── LICENSE
```

---

## Prerequisites

To build and deploy this project, the following are required:

- Docker and Docker Compose installed on the build machine
- A Docker Hub account (or alternative registry)
- TrueNAS SCALE host with Docker runtime enabled
- Cloudflare account with Zero Trust tunnel configured
- Domain registered and DNS managed through Cloudflare

Secrets are managed via environment variables. A `.env` file is required at deploy time:

```
GEMINI_API_KEY=your_key_here
TUNNEL_TOKEN=your_tunnel_token_here
```

> Do not commit `.env` to version control.

---

## Deployment Strategy

Current model: **Local build → Docker Hub → On-Premise pull**

```
1. docker build -t pratiktayde/mindora:test .
2. docker push pratiktayde/mindora:test
3. [On TrueNAS] docker pull pratiktayde/mindora:test
4. docker compose up -d
```

Future iterations will replace this with a CI/CD pipeline via GitHub Actions. See [ROADMAP.md](./ROADMAP.md) — Version 4.

---

## Roadmap

The infrastructure will evolve through the following major milestones:

| Version | Focus | Status |
|---|---|---|
| v1 | Baseline container deployment | ✅ Complete |
| v2 | Reverse proxy (Nginx) | ✅ Complete |
| v3 | Observability (Prometheus + Grafana) | ✅ Complete |
| v4 | CI/CD automation (GitHub Actions) | 🔲 Planned |
| v5 | Persistent storage architecture | 🔲 Planned |
| v6 | Security hardening | 🔲 Planned |
| v7 | Cloud deployment replication | 🔲 Planned |
| v8 | Infrastructure as Code | 🔲 Planned |
| v9 | Advanced experiments | 🔲 Planned |

Full detail: [ROADMAP.md](./ROADMAP.md)

---

## Goals of This Repository

This repository exists to demonstrate the **systematic evolution of a real infrastructure deployment** — from a minimal working baseline toward a production-grade system.

The focus is on:

- Containerisation and WSGI production serving
- Deployment architecture and networking
- Storage reliability and data integrity
- System design thinking applied to real constraints (CGNAT, on-prem hardware)
- Production-oriented engineering practices

---

## License

MIT License