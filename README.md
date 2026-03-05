# Mindora Infrastructure

Infrastructure architecture and deployment configuration for the Mindora application.

This repository documents the containerized deployment, networking architecture, and on-premise infrastructure used to run the Mindora service.

The system is currently deployed on an on-premise TrueNAS server and exposed securely to the internet using Cloudflare Tunnel.

---

## Quick Links

- 🌐 **Live Deployment:** [mindora.pratiktayde.com](https://mindora.pratiktayde.com)
- 🏗 **Architecture Documentation:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- 🗺 **Infrastructure Roadmap:** [ROADMAP.md](./ROADMAP.md)

---

# Project Overview

Mindora is a Flask-based web application deployed using a containerized infrastructure stack.

The goal of this repository is to document the infrastructure architecture used to deploy the application in a production-aware environment.

Key characteristics of the system:

- Containerized application deployment using Docker
- Infrastructure orchestration using Docker Compose
- Secure internet exposure using Cloudflare Tunnel
- On-premise hosting using TrueNAS
- Resilient storage using ZFS pools with redundancy
- Snapshot-based rollback and system configuration backups
- Disk health monitoring via SMART tests
- Periodic ZFS scrub tasks for data integrity verification

The focus of this repository is **infrastructure architecture**, not application development.

---

# Architecture Overview

The system currently follows this architecture:
```
User
 ↓
Cloudflare Edge Network  
 ↓
Cloudflare Tunnel 
 ↓ 
On-Premise TrueNAS Server  
 ↓
Docker Network  
 ↓
Flask Application Container
```
Cloudflare handles TLS termination and edge routing while the application remains hosted inside the private network.

Detailed architecture documentation can be found here:

[Architecture Documentation](./ARCHITECTURE.md)

---

# Infrastructure Components

## Application Container

The application runs inside a Docker container built from a Python slim base image.

The container runs the Flask application using a WSGI server and exposes the service internally on port 5000.

The container is not directly exposed to the public internet.

---

## Docker Compose Deployment

Deployment is orchestrated using Docker Compose.

The compose stack currently includes:

- Mindora application container
- Cloudflare tunnel connector container
- Internal Docker bridge network

Compose configuration is located in:

infra/compose/docker-compose.prod.yml

---

## Cloudflare Tunnel

Because the server operates behind CGNAT, inbound port forwarding is not possible.

Cloudflare Tunnel is used to establish an outbound encrypted connection from the server to Cloudflare's edge network.

This allows secure public access without exposing the internal network.

Public endpoint:

[https://mindora.pratiktayde.com](https://mindora.pratiktayde.com)

---

## On-Premise Infrastructure

The system runs on a dedicated TrueNAS server configured for reliability and data protection.

Key features of the infrastructure:

- ZFS storage pools with redundancy
- Periodic ZFS scrub tasks to verify data integrity
- SMART disk health monitoring
- Snapshot scheduling for rollback capability
- Configuration backups stored off-system for rebuild scenarios

This allows the system to be rebuilt quickly in the event of hardware or OS failure.

---

# Repository Structure

```
mindora-infrastructure
│
├── app                     # Flask application
│
├── docs                    # Architecture documentation
│   └── architecture.md
│
├── infra                   # Infrastructure configuration
│   ├── docker              # Container build configuration
│   │   └── Dockerfile
│   │
│   └── compose             # Deployment orchestration
│       └── docker-compose.prod.yml
│
├── README.md               # Project overview
├── ROADMAP.md              # Planned infrastructure improvements
└── LICENSE
```

---

# Deployment Strategy

Current deployment model:

Local build → Docker Hub → On-Premise Deployment

Deployment steps:

1. Build container image locally
2. Push image to Docker Hub
3. Pull image on the TrueNAS host
4. Deploy containers using Docker Compose

Future iterations will introduce CI/CD automation.

---

# Roadmap

The infrastructure will evolve in multiple phases.

Planned improvements include:

- Reverse proxy layer (Nginx)
- Container health checks
- Improved container isolation
- CI/CD pipeline using GitHub Actions
- Migration to VPS-based deployment for comparison
- Infrastructure observability improvements

Full roadmap available in:

[View the Roadmap](./ROADMAP.md)

---

# Goals of This Repository

This repository exists to demonstrate the evolution of a real infrastructure deployment.

The focus is on:

- Containerization
- Deployment architecture
- Infrastructure reliability
- System design thinking
- Production-oriented engineering practices

---

# License

MIT License