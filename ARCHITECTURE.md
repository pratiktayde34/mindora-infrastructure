# Mindora Infrastructure — v1 Baseline Deployment

## Overview

This document describes the baseline deployment architecture for **Mindora**, a containerized Flask service hosted on an on-premise TrueNAS SCALE server operating behind CGNAT.

The purpose of this project is not application development but the exploration of **practical infrastructure and deployment patterns**. The system is intentionally designed to evolve incrementally — beginning with a minimal functional architecture and gradually introducing more advanced infrastructure layers.

The current state represents **Version 1 — Baseline Container Deployment**, focused on establishing:

- reliable service execution
- controlled public exposure
- reproducible container deployments
- resilient on-prem infrastructure

Future iterations will extend the system with additional architectural layers including reverse proxy separation, observability infrastructure, automated deployments, and cloud replication.

---

# Infrastructure Environment

The service runs on a self-hosted infrastructure node powered by **TrueNAS SCALE**, which serves as the container host and storage platform.

The environment was designed with the following operational priorities:

- long-term storage reliability
- infrastructure recoverability
- separation of runtime and persistent storage
- proactive disk health monitoring

The system implements multiple layers of redundancy and integrity verification to reduce the risk of data loss and to simplify recovery in the event of hardware failure.

---

# Hardware Layout

The system separates the operating system, persistent storage, and application workloads across dedicated devices.

This separation prevents application workloads from interfering with storage operations and simplifies recovery procedures.

```
TrueNAS Host
│
├── Boot Device
│ └── SSD (TrueNAS Operating System)
│
├── Data Pool (tank)
│ ├── HDD 1
│ └── HDD 2
│
└── Applications Pool (apps)
└── Dedicated SSD
```


Key design goals:

- isolate OS from runtime workloads
- isolate application workloads from persistent storage
- maintain high reliability for critical data

---

# Storage Architecture

## Data Pool — `tank`

The primary storage pool is configured as a **ZFS mirrored pool across two HDDs**.

Purpose:

- persistent storage
- SMB shares
- backup destination for application data

Dataset layout:

```
tank/
├── smb-share-1
├── smb-share-2
└── backups/
```


Characteristics:

- mirrored disk configuration
- protection against single disk failure
- uninterrupted operation during disk replacement

If one disk fails, the mirror continues serving data while the failed drive can be replaced without downtime.

---

## Applications Pool — `apps`

Application workloads are isolated onto a **dedicated SSD-based ZFS pool**.

Purpose:

- host container runtime workloads
- provide high-performance IO for containers
- isolate application IO from persistent storage IO

Dataset layout:

```
apps/
├── compose/
└── volumes/
```


**compose/**  
Stores container orchestration definitions such as Docker Compose files and service configuration.

**volumes/**  
Reserved for persistent runtime data including databases, application state, and uploaded files.

---

# Data Integrity and Reliability

The infrastructure relies heavily on **ZFS integrity mechanisms and hardware diagnostics**.

## ZFS Snapshots

Periodic snapshots are configured on datasets to allow **point-in-time recovery**.

Snapshots allow recovery from:

- accidental deletion
- configuration mistakes
- corrupted application state

Snapshots make it possible to restore previous dataset states quickly.

---

## ZFS Scrub Operations

Scheduled **ZFS scrub tasks** verify the integrity of stored data.

Scrubbing performs:

- block-level checksum validation
- detection of silent data corruption
- automatic correction using mirrored disk data

Regular scrub operations ensure latent storage errors are detected and corrected early.

---

## SMART Disk Monitoring

All storage devices are monitored through **SMART diagnostics**.

Scheduled tests include:

- short SMART tests
- extended SMART tests

These tests monitor indicators such as:

- bad sector development
- disk degradation
- read/write error rates
- early hardware failure signals

This monitoring allows failing disks to be replaced proactively.

---

# Recovery and Rebuild Strategy

The infrastructure is designed so that **complete system recovery can be performed quickly without manual reconstruction**.

## TrueNAS Configuration Backup

TrueNAS allows exporting the full system configuration as a backup file.

The configuration backup includes:

- storage pool definitions
- dataset structure
- network configuration
- system users and permissions
- container runtime configuration

Configuration backups are stored externally in cloud storage.

If the boot SSD fails:

1. Install TrueNAS on a replacement drive  
2. Import the existing ZFS pools  
3. Restore the configuration backup  

The system will return to the exact same operational state.

---

## Application Data Protection

Application runtime workloads operate on the SSD-based `apps` pool, while critical data is backed up to the mirrored HDD pool.

Example backup flow:

```
apps/volumes/
↓
replicated to
↓
tank/backups/
```


This architecture combines:

- **SSD performance for application runtime**
- **HDD redundancy for long-term durability**

If the SSD fails, the system can be rebuilt and application data restored from the mirrored HDD pool.

---

# Container Runtime Environment

Container workloads run on **TrueNAS SCALE's Docker runtime environment**.

When the applications pool is assigned for container workloads, TrueNAS automatically provisions an internal dataset:

```
/mnt/.ix-apps
```

This dataset stores:

- container images
- container layers
- container metadata
- runtime state

Container storage configuration:

```
Storage driver: overlay2
Backing filesystem: ZFS
```


This allows container storage to inherit the integrity guarantees of ZFS.

---

# Domain and DNS Configuration

The public domain is registered through **Cloudflare Registrar**.

```
pratiktayde.com
```


Cloudflare manages DNS and edge network functionality.

Cloudflare services used in this architecture:

- DNS resolution
- CDN edge routing
- Web Application Firewall
- Cloudflare Tunnel ingress

The service is exposed via the subdomain:

```
mindora.pratiktayde.com
```


---

# Application Containerization

The application itself is a Flask service.

The Flask development server (`flask run`) is not suitable for production environments, so the application is served using **Gunicorn**, a production-grade WSGI server.

Example Dockerfile:

```
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


Gunicorn provides:

- multi-worker request handling
- stable process management
- production-grade HTTP serving

---

# Container Image Build Process

The container image is built locally before deployment.

```
docker build -t mindora:test .
```

Image verification:

```
docker images  
```

---

# Local Container Validation

Before publishing the image, the container is tested locally.

```
docker run -p 5000:5000 mindora:test
```

This verifies that the containerized application executes correctly.

---

# Container Registry

A Docker Hub repository is used as the container registry.

```
pratiktayde/mindora
```

Authentication is performed using the Docker CLI:

```
docker login
```

---

# Image Distribution

The built container image is tagged and pushed to Docker Hub.

```
docker tag mindora:test pratiktayde/mindora:test
```
```
docker push pratiktayde/mindora:test
```

This allows remote hosts to pull the container image.

---

# Deployment to TrueNAS

The NAS pulls the container image from Docker Hub.

```
docker pull pratiktayde/mindora:test
```

Image verification:

```
docker images
```

---

# Container Orchestration

Manual container execution was replaced with **Docker Compose**, allowing declarative infrastructure definitions.

Compose files are stored at:

```
/mnt/apps/compose/mindora
```

Example configuration:

```
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

Deployment command:

```
docker compose up -d
```

Container verification:

```
docker ps 
```

---

# Public Exposure via Cloudflare Tunnel

The NAS operates behind **Carrier-Grade NAT**, which prevents inbound port forwarding.

To expose the service securely without opening router ports, the system uses **Cloudflare Tunnel**, which creates an outbound-initiated connection from the NAS to Cloudflare's edge network.

---

# Tunnel Configuration

A tunnel was created in Cloudflare Zero Trust:

```
mindora-tunnel
```

Tunnel type:

```
cloudflared
```

Cloudflare provides an authentication token used by the cloudflared container.

---

# Public Hostname Routing

Cloudflare routing configuration:

```
Hostname: mindora.pratiktayde.com
Service Type: HTTP
Service URL: mindora:5000
```

Incoming requests are forwarded to the container through the internal Docker network.

---

# Traffic Flow

```
User
↓
Cloudflare Edge
↓
Cloudflare Tunnel
↓
cloudflared container
↓
Docker network
↓
mindora container
```

---

# Baseline Architecture (v1)

```
User
↓
Cloudflare (DNS + TLS + WAF)
↓
Cloudflare Tunnel
↓
TrueNAS Host
↓
Docker Network
↓
Flask Application (Gunicorn)
```

---

# Current Limitations

The baseline deployment intentionally remains minimal and does not yet include:

- reverse proxy separation
- container privilege hardening
- container health checks
- resource limits
- CI/CD automation
- observability stack
- multi-node orchestration
- cloud deployment replication

These improvements will be introduced progressively in future iterations.