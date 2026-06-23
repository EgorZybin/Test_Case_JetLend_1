# Заказы с промокодами

Django REST API для создания заказов с опциональной скидкой по промокоду.

## Требования

- Python 3.10+
- Django 4.2+
- PostgreSQL 16+ (через Docker Compose)

## Быстрый старт (Docker)

```bash
docker compose up --build
```

API: http://127.0.0.1:8000/api/orders/

Демо-данные загружаются автоматически при старте (`seed_demo_data`).

### Полезные команды

```bash
# запуск в фоне
docker compose up -d --build

# тесты
docker compose run --rm web python manage.py test orders

# django shell
docker compose exec web python manage.py shell

# остановка
docker compose down
```

## Локальная разработка (без Docker)

Поднимите PostgreSQL локально, затем:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export POSTGRES_DB=orders
export POSTGRES_USER=orders
export POSTGRES_PASSWORD=orders
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432

python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Или скопируйте `.env.example` и экспортируйте переменные из него.

## API

### Создание заказа

`POST /api/orders/`

Запрос:

```json
{
  "user_id": 1,
  "goods": [{ "good_id": 1, "quantity": 2 }],
  "promo_code": "SUMMER2025"
}
```

Ответ `201 Created`:

```json
{
  "user_id": 1,
  "order_id": 1,
  "goods": [
    {
      "good_id": 1,
      "quantity": 2,
      "price": 100,
      "discount": "0.1",
      "total": 180
    }
  ],
  "price": 200,
  "discount": "0.1",
  "total": 180
}
```

Поле `promo_code` необязательное.

Пример:

```bash
curl -X POST http://127.0.0.1:8000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"goods":[{"good_id":1,"quantity":2}],"promo_code":"SUMMER2025"}'
```

### Правила промокода

- промокод должен существовать и быть активным (не просрочен, не исчерпан);
- один пользователь может использовать промокод только один раз;
- промокод может быть ограничен категорией товаров;
- товары с `exclude_from_promotions=True` не получают скидку;
- скидка применяется построчно к подходящим товарам, итог заказа — сумма строк;
- `discount` на уровне заказа — **эффективная** ставка: `(price - total) / price`, а не номинал промокода.

### Формат ошибок

Ошибки бизнес-логики возвращают `400 Bad Request`:

```json
{
  "error": "Promo code has expired.",
  "code": "promo_code_expired"
}
```

Ошибки валидации тела запроса — в стандартном формате DRF.

Коды ошибок:

| code | Описание |
|------|----------|
| `user_not_found` | Пользователь не найден |
| `good_not_found` | Товар не найден |
| `invalid_order_items` | Пустой список товаров |
| `promo_code_not_found` | Промокод не найден |
| `promo_code_expired` | Промокод просрочен |
| `promo_code_exhausted` | Лимит использований исчерпан |
| `promo_code_already_used` | Пользователь уже использовал промокод |

## Тесты

Через Docker:

```bash
docker compose run --rm web python manage.py test orders
```

С локальным PostgreSQL:

```bash
python manage.py test orders
```

## Структура проекта

- `orders/models.py` — доменные модели
- `orders/services/` — бизнес-логика заказов и промокодов
- `orders/views.py` — HTTP-слой
- `orders/serializers.py` — валидация и форматирование запроса/ответа
- `docker-compose.yml` — PostgreSQL + web-сервис
- `build/Dockerfile` — образ приложения
- `build/entrypoint.sh` — ожидание БД, migrate, seed, runserver
