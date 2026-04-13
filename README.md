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
