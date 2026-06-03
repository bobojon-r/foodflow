# FoodFlow

Учебный pet-project — платформа доставки еды, построенная по принципам микросервисной архитектуры. Цель проекта: освоить на практике технологии, которые используются в production-системах уровня senior.

## Что реализовано

| Этап | Технологии | Статус |
|------|-----------|--------|
| Монолит | FastAPI, SQLAlchemy 2.0, Alembic, JWT, pytest | ✅ |
| Микросервисы | 5 независимых сервисов, database-per-service, HTTP между сервисами | ✅ |
| Kafka | Event-driven коммуникация, KRaft (без Zookeeper), aiokafka | ✅ |
| Stripe | PaymentIntent API, webhooks, graceful degradation | ✅ |
| Telegram-бот | aiogram 3, подписчики, уведомления по событиям Kafka | ✅ |
| Kubernetes | minikube, Helm chart, HPA, StatefulSet для Kafka | ✅ |
| CI/CD | GitHub Actions — lint (ruff) + тесты + build + push в ghcr.io | ✅ |
| AWS | Terraform: EKS, RDS PostgreSQL, MSK Kafka, ECR, VPC, IAM | ✅ |
| Observability | Prometheus + Grafana, Jaeger (OpenTelemetry), Sentry | ✅ |

## Архитектура

```
                    ┌─────────────────────────────────┐
                    │           Клиент / API           │
                    └────────────────┬────────────────┘
                                     │ HTTP
          ┌──────────────────────────┼──────────────────────┐
          │                          │                       │
   ┌──────▼──────┐          ┌────────▼───────┐   ┌──────────▼────────┐
   │ auth-service│          │  order-service │   │restaurant-service │
   │   :8001     │          │    :8003       │   │      :8002        │
   └─────────────┘          └────────┬───────┘   └───────────────────┘
                                     │
                              Kafka (order.created)
                                     │
                    ┌────────────────┼────────────────┐
                    │                                  │
           ┌────────▼────────┐              ┌──────────▼───────────┐
           │ payment-service │              │ notification-service  │
           │    :8004        │              │       :8005           │
           │  Stripe API     │              │  Telegram / логи      │
           └────────┬────────┘              └──────────────────────┘
                    │
             Kafka (payment.succeeded)
                    │
           notification-service
```

**Kafka топики:**
- `order.created` — создан новый заказ
- `order.status_changed` — изменился статус заказа
- `payment.succeeded` — платёж прошёл успешно
- `payment.failed` — платёж не прошёл

## Структура репозитория

```
foodflow/
├── services/
│   ├── monolith/              # Этап 1: монолитное приложение
│   ├── auth-service/          # JWT авторизация (порт 8001)
│   ├── restaurant-service/    # Рестораны и меню (порт 8002)
│   ├── order-service/         # Заказы + Kafka producer (порт 8003)
│   ├── payment-service/       # Stripe + Kafka consumer (порт 8004)
│   └── notification-service/  # Telegram бот + Kafka consumer (порт 8005)
├── helm/foodflow/             # Helm chart для Kubernetes
├── terraform/                 # AWS инфраструктура (EKS, RDS, MSK, ECR)
├── monitoring/                # Prometheus config, Grafana provisioning
├── .github/workflows/         # CI (тесты) + CD (build → ghcr.io)
├── docker-compose.yml         # Локальный запуск всего стека
└── .env.example               # Пример переменных окружения
```

## Быстрый старт

### 1. Клонировать и настроить переменные

```bash
git clone https://github.com/bobojon-r/foodflow.git
cd foodflow
cp .env.example .env
# Отредактируй .env — минимум SECRET_KEY и POSTGRES_PASSWORD
```

### 2. Запустить

```bash
docker compose up --build
```

Сервисы поднимаются автоматически, Alembic-миграции применяются при старте.

### 3. Проверить работу

```bash
# Регистрация
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass1234","full_name":"User"}'

# Логин
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=pass1234"
```

### 4. API документация

| Сервис | Swagger UI |
|--------|-----------|
| auth-service | http://localhost:8001/docs |
| restaurant-service | http://localhost:8002/docs |
| order-service | http://localhost:8003/docs |
| payment-service | http://localhost:8004/docs |
| notification-service | http://localhost:8005/docs |

## Переменные окружения

Все секреты хранятся в `.env` (файл в `.gitignore`, никогда не коммитится).

Скопируй `.env.example` → `.env` и заполни:

| Переменная | Описание | Где взять |
|------------|----------|-----------|
| `POSTGRES_PASSWORD` | Пароль БД | Придумать самому |
| `SECRET_KEY` | JWT секрет | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `STRIPE_SECRET_KEY` | Stripe API ключ | [dashboard.stripe.com](https://dashboard.stripe.com/test/apikeys) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook секрет | `stripe listen --forward-to localhost:8004/api/v1/webhooks/stripe` |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `SENTRY_DSN` | Sentry DSN (опционально) | [sentry.io](https://sentry.io) |

## Stripe (Этап 4)

Сервис оплаты создаёт Stripe PaymentIntent при каждом новом заказе.

**Flow:**
```
order.created (Kafka) → PaymentIntent (Stripe API) → payment.succeeded (Kafka)
```

**Без `STRIPE_SECRET_KEY`** — сервис работает в режиме симуляции: сразу публикует `payment.succeeded` без обращения к Stripe. Удобно для разработки.

**Для локального тестирования webhooks:**
```bash
stripe listen --forward-to localhost:8004/api/v1/webhooks/stripe
# Скопируй whsec_... в .env → STRIPE_WEBHOOK_SECRET
```

## Telegram-бот (Этап 5)

Notification-service слушает Kafka и рассылает уведомления всем подписчикам бота.

**Как подписаться:** найди бота в Telegram → `/start`

**Без `TELEGRAM_BOT_TOKEN`** — сервис работает, уведомления идут только в логи.

| Событие | Сообщение |
|---------|-----------|
| `order.created` | 🆕 Новый заказ #ID — сумма |
| `order.status_changed` | 📦 Заказ #ID: статус A → B |
| `payment.succeeded` | ✅ Оплата прошла для заказа #ID |

## Observability (Этап 9)

| Инструмент | URL | Назначение |
|-----------|-----|-----------|
| Prometheus | http://localhost:9090 | Метрики всех сервисов |
| Grafana | http://localhost:3000 | Дашборды (admin/admin) |
| Jaeger | http://localhost:16686 | Распределённые трейсы |
| `/metrics` | http://localhost:800X/metrics | Prometheus endpoint каждого сервиса |

**Grafana:** Datasource Prometheus добавляется автоматически. Для готового дашборда импортируй ID `14382` (FastAPI Observability).

## Kubernetes (Этап 6)

```bash
# Запуск локально (minikube)
minikube start
eval $(minikube docker-env)

# Собрать образы
for svc in auth-service restaurant-service order-service payment-service notification-service; do
  docker build -t foodflow-$svc ./services/$svc
done

# Задеплоить
helm upgrade --install foodflow ./helm/foodflow

# Получить URL сервисов
minikube service list
```

## AWS (Этап 8)

Terraform поднимает полную production-инфраструктуру в AWS:

- **EKS** — Kubernetes кластер (t3.medium nodes)
- **RDS** — PostgreSQL 16 (db.t3.micro)
- **MSK** — Managed Kafka (kafka.t3.small, 2 брокера)
- **ECR** — Docker registry для всех 5 сервисов
- **VPC** — изолированная сеть, private/public subnets, NAT gateway

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Заполни terraform.tfvars

terraform init
terraform plan
terraform apply   # ~15-20 минут

# Подключиться к кластеру
aws eks update-kubeconfig --name foodflow-prod --region eu-west-1
```

## CI/CD (Этап 7)

**CI** (`.github/workflows/ci.yml`) — запускается на каждый push:
- `ruff check` — линтинг всех сервисов
- `pytest` — тесты с SQLite in-memory (без внешних зависимостей)

**CD** (`.github/workflows/cd.yml`) — запускается при push в `main`:
- Собирает Docker образы всех 5 сервисов
- Пушит в `ghcr.io/bobojon-r/foodflow-{service}:sha-{git_sha}`

## Что можно улучшить

- **API Gateway** — единая точка входа (nginx/Traefik) вместо 5 открытых портов
- **Тесты для payment-service и notification-service** — сейчас только у auth/restaurant/order
- **Kubernetes Secrets из Vault** — сейчас пароли в values.yaml, в prod нужен HashiCorp Vault или AWS Secrets Manager
- **Alembic миграции в K8s** — запускать как Job перед деплоем, а не через `create_all`
- **Rate limiting** — защита API от злоупотреблений (FastAPI Limiter или nginx)
- **Интеграционные тесты** — тесты между сервисами через реальный Kafka (testcontainers)
- **Retry + DLQ** — Dead Letter Queue для Kafka событий, которые не удалось обработать

## Принципы разработки

- **Async-first** — весь код асинхронный, от роутов до запросов к БД
- **Database-per-service** — каждый сервис владеет своей БД, нет shared databases
- **Event-driven** — между сервисами через Kafka, HTTP только где нужна синхронность
- **12-factor app** — конфиг через env, stateless сервисы, логи в stdout
- **Graceful degradation** — Stripe/Telegram/Sentry отключены без ключей, сервис продолжает работать

## Автор

Python backend developer, 3+ года опыта с FastAPI, Django, aiogram. Проект создан для практического освоения инфраструктурных технологий.
