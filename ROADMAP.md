# Mindora Infrastructure Roadmap

This document defines the **long-term infrastructure evolution plan** for the Mindora deployment.

The purpose of this project is **not application development**, but the systematic development of **production-grade infrastructure thinking** through incremental architectural evolution.

Each version milestone represents a **meaningful infrastructure capability upgrade**, not minor configuration changes.

The project follows a foundational systems engineering principle:

“A complex system that works is invariably found to have evolved from a simple system that worked.” — John Gall

The roadmap therefore evolves the system through layers of **networking, reliability, security, automation, and observability**.

---

# Current Architecture (Baseline)

Mindora is currently deployed using a **self-hosted on-premise infrastructure**.

Architecture:

User
↓
Cloudflare DNS
↓
Cloudflare Tunnel (CGNAT bypass)
↓
TrueNAS On-Prem Server
↓
Docker Runtime
↓
Flask Application Container (Gunicorn)

Infrastructure characteristics:

• On-premise deployment
• ZFS storage with redundancy
• Containerized application runtime
• Secure inbound connectivity via Cloudflare Tunnel
• Docker image registry via Docker Hub
• Environment variable based secret management
• Manual image build → push → pull deployment pipeline

This deployment is considered **Version 1: Baseline Container Deployment**.

---

# Version 2 — Reverse Proxy Architecture

## Objective

Introduce a dedicated **reverse proxy layer** to separate traffic routing from application execution.

This reflects the standard architecture used in production container environments.

## Architecture

User
↓
Cloudflare DNS
↓
Cloudflare Tunnel
↓
Nginx Reverse Proxy Container
↓
Flask Application Container

## Capabilities Introduced

• Layered request routing
• Reverse proxy traffic handling
• Separation of routing and application responsibilities
• Future compatibility with load balancing and scaling

## Implementation Tasks

• Add Nginx container to compose stack
• Configure internal container networking
• Route HTTP traffic through Nginx
• Remove direct exposure of application container
• Implement proper proxy headers
• Configure request buffering and timeout settings

## Deliverables

• nginx configuration
• updated docker-compose architecture
• architecture documentation update

---

# Version 3 — Infrastructure Observability

## Objective

Introduce system visibility through **metrics and monitoring infrastructure**.

Operating infrastructure without observability prevents reliable operations.

## Architecture Additions

Prometheus
Grafana
Node Exporter
cAdvisor

## Architecture

User
↓
Cloudflare
↓
Tunnel
↓
Reverse Proxy
↓
Application Containers

Monitoring Stack

Prometheus
↓
Metrics Collection
↓
Grafana Dashboards

## Capabilities Introduced

• Host system monitoring
• Container resource monitoring
• Performance visibility
• Operational dashboards

## Implementation Tasks

• Deploy Prometheus metrics collector
• Deploy Node Exporter for host metrics
• Deploy cAdvisor for container metrics
• Deploy Grafana for visualization
• Create dashboards for:

CPU usage
memory usage
container restart events
disk IO
network throughput

## Deliverables

• Prometheus configuration
• Grafana dashboards
• monitoring documentation

---

# Version 4 — Deployment Automation

## Objective

Replace the manual deployment process with a **fully automated build and deployment pipeline**.

## Current Deployment

Developer machine
↓
Docker build
↓
Docker push
↓
NAS pull
↓
Container restart

## Target Deployment

Git push
↓
CI pipeline builds container
↓
Image pushed to registry
↓
Server automatically pulls latest image
↓
Containers redeployed

## Capabilities Introduced

• Continuous Integration
• Automated image builds
• Deployment consistency
• Reduced operational friction

## Implementation Tasks

• Implement GitHub Actions workflow
• Automate Docker image builds
• Automate registry publishing
• Secure automated SSH deployment
• Implement automated container updates

## Deliverables

• CI pipeline configuration
• automated build logs
• deployment documentation

---

# Version 5 — Persistent Storage Architecture

## Objective

Separate application runtime from persistent state.

The current system treats application data as ephemeral container state.

This version introduces **durable storage architecture**.

## Architecture

Application Container
↓
Mounted Persistent Volume
↓
ZFS Dataset

## Capabilities Introduced

• Durable application state
• Storage lifecycle management
• Data protection via ZFS snapshots

## Implementation Tasks

• Create dedicated dataset for application data
• Mount persistent storage into container runtime
• Configure snapshot schedules
• Validate persistence across container restarts
• Implement backup policy

## Deliverables

• persistent storage configuration
• storage architecture documentation

---

# Version 6 — Infrastructure Security

## Objective

Introduce security hardening across the infrastructure stack.

## Capabilities Introduced

• network isolation
• hardened container runtime
• traffic filtering
• request rate control

## Implementation Tasks

• isolate container networks
• restrict exposed services
• implement reverse proxy rate limiting
• configure Cloudflare security rules
• audit container privileges
• reduce container attack surface

## Deliverables

• security architecture documentation
• hardened network configuration

---

# Version 7 — Cloud Deployment Replication

## Objective

Deploy the same architecture on public cloud infrastructure to compare **on-prem vs cloud deployment characteristics**.

## Architecture

Internet
↓
Cloudflare DNS
↓
VPS Public IP
↓
Reverse Proxy
↓
Application Containers

## Capabilities Introduced

• public cloud deployment
• firewall configuration
• infrastructure portability

## Implementation Tasks

• provision VPS environment
• configure firewall rules
• deploy container stack
• document deployment differences
• compare latency and reliability characteristics

## Deliverables

• cloud deployment documentation
• architecture comparison analysis

---

# Version 8 — Infrastructure as Code

## Objective

Convert infrastructure configuration into **reproducible code**.

Infrastructure should be reproducible, not manually configured.

## Capabilities Introduced

• repeatable deployments
• version-controlled infrastructure
• automated provisioning

## Implementation Tasks

• document infrastructure setup
• automate provisioning steps
• introduce infrastructure automation tools
• build reproducible deployment workflows

## Deliverables

• infrastructure provisioning scripts
• automated deployment documentation

---

# Version 9 — Advanced Infrastructure Experiments

## Objective

Explore advanced distributed infrastructure patterns.

These experiments expand infrastructure understanding beyond single-node deployments.

## Areas of Exploration

• container orchestration systems
• distributed service discovery
• service mesh networking
• large-scale monitoring pipelines
• failure injection testing
• multi-region failover architecture

These experiments are intended for **learning and architectural exploration**, not production deployment.

---

# Development Principles

This project follows several infrastructure engineering principles:

• stability before complexity
• separation of concerns
• observability as a requirement
• automation over manual processes
• infrastructure documented alongside implementation

---

# Documentation Requirements

Every architecture upgrade must update:

README.md
ARCHITECTURE.md
CHANGELOG.md

Each version must include:

• architecture diagram
• explanation of architectural changes
• operational considerations

---

# Long Term Goal

By the final stages, the repository should demonstrate:

• real infrastructure deployment experience
• container networking expertise
• automated deployment pipelines
• monitoring and observability infrastructure
• secure system design

The project is intended to function as a **public infrastructure case study** rather than a simple application repository.
