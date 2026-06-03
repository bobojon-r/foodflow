# FoodFlow

Pet-project для изучения микросервисной архитектуры и современного backend-стека. Платформа доставки еды, построенная как система независимых сервисов, взаимодействующих через Kafka и HTTP.

## Цель проекта

Практическое освоение технологий, востребованных в senior-вакансиях:
- Микросервисная архитектура
- Apache Kafka (event-driven коммуникация)
- Docker и Docker Compose
- Kubernetes (minikube локально, EKS в AWS)
- CI/CD через GitHub Actions
- AWS (EKS, RDS, MSK, ECR, S3, CloudWatch)
- Интеграция платёжной системы (Stripe)
- Terraform (Infrastructure as Code)
- Наблюдаемость: Prometheus, Grafana, Sentry, OpenTelemetry

## Бизнес-домен

Платформа доставки еды с тремя типами пользователей:
- **Клиент** — просматривает рестораны, создаёт заказы, оплачивает, отслеживает статус
- **Владелец ресторана** — управляет меню, принимает заказы, меняет статус
- **Курьер** — получает назначения, обновляет статус доставки

## Архитектура

Проект развивается в несколько этапов — от монолита к полноценной микросервисной системе в облаке.

### Финальная архитектура (цель)


┌─────────────┐
                │ API Gateway │
                └──────┬──────┘
                       │
   ┌───────────────────┼───────────────────┐
   │                   │                   │
   ┌────▼────┐       ┌──────▼──────┐      ┌─────▼────┐
│  Auth   │       │   Order     │      │Restaurant│
│ Service │       │  Service    │      │ Service  │
└─────────┘       └──────┬──────┘      └──────────┘
│
┌──────▼──────┐
│    Kafka    │
└──────┬──────┘
│
┌───────────────────┼───────────────────┐
│                   │                   │
┌────▼─────┐      ┌──────▼──────┐      ┌─────▼────┐
│ Payment  │      │Notification │      │Analytics │
│ Service  │      │  Service    │      │ Service  │
└──────────┘      └─────────────┘      └──────────┘


### Сервисы

| Сервис | Ответственность | Стек |
|--------|-----------------|------|
| api-gateway | Единая точка входа, роутинг, rate limiting | FastAPI |
| auth-service | Регистрация, JWT, роли | FastAPI + Postgres |
| order-service | CRUD заказов, бизнес-логика заказа | FastAPI + Postgres + Kafka producer |
| restaurant-service | Рестораны, меню, блюда | FastAPI + Postgres |
| payment-service | Stripe интеграция, webhooks | FastAPI + Postgres + Kafka |
| notification-service | Email, Telegram-бот | FastAPI + aiogram + Kafka consumer |
| delivery-service | Назначение курьеров, трекинг | FastAPI + Postgres + Kafka |
| analytics-service | Сбор метрик, отчёты | FastAPI + Kafka consumer |

У каждого сервиса своя база данных — принцип database-per-service.

## Технологический стек

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy 2.0 (async) + asyncpg
- Alembic (миграции)
- Pydantic v2
- aiogram (Telegram-бот)
- aiokafka (Kafka клиент)

### Инфраструктура
- Postgres 16
- Apache Kafka
- Redis (кеш, rate limiting)
- Docker, Docker Compose
- Kubernetes (minikube → EKS)
- Helm charts

### DevOps / Cloud
- GitHub Actions (CI/CD)
- Terraform (IaC)
- AWS: EKS, RDS, MSK, ECR, S3, Route53, ACM, CloudWatch

### Наблюдаемость
- Prometheus + Grafana
- Loki (логи)
- Sentry (ошибки)
- OpenTelemetry (трейсинг)

## Roadmap

Проект развивается поэтапно. Каждая новая технология вводится только когда предыдущий этап стабилен.

- [x] **Этап 1: Монолит** — FastAPI + Postgres в Docker Compose. Базовая бизнес-логика: users, restaurants, menu, orders.
- [x] **Этап 2: Распил на микросервисы** — разделение на auth, order, restaurant, payment. Синхронное общение через HTTP.
- [x] **Этап 3: Kafka** — переход на event-driven архитектуру. Топики: `order.created`, `order.paid`, `payment.succeeded` и т.д.
- [ ] **Этап 4: Stripe** — интеграция платежей, webhooks, идемпотентность.
- [x] **Этап 5: Telegram-бот** — notification-service на aiogram, уведомления о статусе заказа.
- [x] **Этап 6: Kubernetes локально** — minikube, Helm, автоскейлинг.
- [x] **Этап 7: CI/CD** — GitHub Actions, автоматические тесты, сборка, деплой.
- [x] **Этап 8: AWS** — EKS, RDS, MSK, Terraform, production-ready инфраструктура.
- [x] **Этап 9: Observability** — Prometheus, Grafana, Sentry, OpenTelemetry.

## Telegram-бот (Этап 5)

Сервис уведомлений (`notification-service`) слушает события из Kafka и отправляет сообщения в Telegram всем подписчикам.

### Как создать бота и получить токен

1. Открой Telegram и найди **[@BotFather](https://t.me/BotFather)**
2. Отправь команду `/newbot`
3. Введи имя бота (например: `FoodFlow Notifications`)
4. Введи username (например: `foodflow_notify_bot`) — должен заканчиваться на `bot`
5. BotFather выдаст токен вида:

   ```
   1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
   ```

6. Скопируй токен и добавь в файл `.env` в корне проекта:

   ```env
   TELEGRAM_BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
   ```

7. Запусти проект:

   ```bash
   docker compose up --build
   ```

8. Найди своего бота в Telegram, отправь `/start` — он добавит тебя в подписчики
9. Создай заказ через API — придёт уведомление в Telegram

### Что присылает бот

| Событие Kafka | Сообщение в Telegram |
|---------------|----------------------|
| `order.created` | 🆕 Новый заказ #ID, сумма |
| `order.status_changed` | 📦 Заказ #ID: статус A → B |
| `payment.succeeded` | ✅ Оплата прошла для заказа #ID |

> **Примечание:** без `TELEGRAM_BOT_TOKEN` сервис работает в обычном режиме — только логи. Бот отключён, Kafka consumer продолжает работать.

## Структура репозитория

## Принципы разработки

- **Async-first** — весь код асинхронный, от эндпоинтов до работы с БД.
- **Database-per-service** — каждый микросервис владеет своей БД, никаких shared databases.
- **Event-driven** — между сервисами предпочтение асинхронным событиям через Kafka.
- **Идемпотентность** — все операции, которые могут повториться (webhooks, consumers), идемпотентны.
- **Тесты обязательны** — pytest для unit и integration тестов в каждом сервисе.
- **12-factor app** — конфигурация через env, stateless сервисы, логи в stdout.

## Автор

Python backend developer, 3+ года опыта с FastAPI, Django, aiogram. Проект создан для практического освоения инфраструктурных технологий.