# PromptCart 🛒

> Connect local vendors to customers over WhatsApp.

PromptCart is an event-driven microservices platform that lets customers browse catalogs, place orders, and receive updates entirely through WhatsApp chat.

## Architecture Overview

| # | Service | Stack |
|---|---------|-------|
| 1 | **WhatsApp Gateway** ← *we are here* | Python / FastAPI / Redis |
| 2 | Conversation Orchestrator | Node.js / Go |
| 3 | AI Sales Agent | Python / FastAPI |
| 4 | Catalog Service | Go / Postgres |
| 5 | Vendor Management | Node.js / Postgres |
| 6 | Order Service | Go / Postgres |
| 7 | Fulfillment Adapters | Python / Go |
| 8 | Delivery Orchestrator | Node.js |
| 9 | Notification Service | Python |

Communication: **gRPC/REST** (sync) · **Redis Pub/Sub → RabbitMQ/Kafka** (async events)

## Phase 1 – WhatsApp Gateway (Tracer Bullet)

```
services/
└── whatsapp-gateway/   # Microservice 1
    ├── app/
    │   └── main.py
    ├── test_webhook.py
    ├── requirements.txt
    ├── Dockerfile
    ├── docker-compose.yaml
    └── .env.example
```

### Quick Start

```bash
cd services/whatsapp-gateway
cp .env.example .env        # set VERIFY_TOKEN
docker compose up --build
```

### Tests (no Docker needed)

```bash
cd services/whatsapp-gateway
pip install -r requirements.txt
pytest test_webhook.py -v
```

### Verify Webhook Challenge

```bash
curl "http://localhost:8000/webhook?hub.mode=subscribe&hub.verify_token=my_secure_verify_token&hub.challenge=hello123"
# → hello123
```

### Send a Test Message

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"object":"whatsapp_business_account","entry":[]}'
# → {"status":"received"}
```

## Phase 2 — Vendor Management Service (Microservice 2/9)
The Vendor Management Service provides the CRUD backbone for registering Dark Stores and Local Shopkeepers. It runs async SQLAlchemy via FastAPI on port 8001.

```
File Layout
services/
└── vendor-management/
    ├── app/
    │   ├── main.py          ← FastAPI init + lifecycle
    │   ├── database.py      ← Async SQLAlchemy config
    │   ├── models.py        ← DB declarative schema (UUID, Name, Type)
    │   ├── schemas.py       ← Pydantic validatiors
    │   └── routers/
    │       └── vendors.py   ← Standard 5 CRUD endpoints
    ├── test_vendor_api.py   ← 6 pytest workflows mocking SQLite async DB
    ├── Dockerfile
    ├── .env.example
    ├── requirements.txt
    └── docker-compose.yaml  ← api + postgres:15-alpine stack
API Endpoints
Method	Path	Purpose
POST	/api/v1/vendors	Create Dark Store/Shopkeeper
GET	/api/v1/vendors	List active vendors (Filters: ?type=)
GET	/api/v1/vendors/{id}	Fetch highly specific vendor
PATCH	/api/v1/vendors/{id}	Edit vendor data
DELETE	/api/v1/vendors/{id}	Soft-delete vendor (is_active=False)
```
