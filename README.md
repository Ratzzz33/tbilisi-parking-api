# Tbilisi Parking API

REST API для автоматизации парковки в Тбилиси через [municipal.gov.ge](https://parking.tbilisi.gov.ge).

Работает напрямую с официальным API, используя Bearer JWT-токен.  
Не требует SMS, 2FA, телефона или мобильного приложения — только токен.

## Возможности

- ✅ Просмотр баланса (GEL) и информации о пользователе
- ✅ Список всех машин (42 у автора)
- ✅ Постановка на парковку по адресу/номеру места
- ✅ Снятие с парковки
- ✅ Поиск парковочных мест по адресу
- ✅ История парковок
- ✅ Тарифы и абонементы
- ✅ Полная Swagger-документация
- ✅ **Несколько машин одновременно** — без ограничений

## Быстрый старт

```bash
git clone git@github.com:Ratzzz33/tbilisi-parking-api.git
cd tbilisi-parking-api

# Установка
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Настройка
cp .env.example .env
# Вставьте токен в .env:
# PARKING_TOKEN=eyJhbGciOiJIUzI1NiIs...
```

### Как получить токен

1. Откройте https://parking.tbilisi.gov.ge
2. Нажмите F12 → Application → Local Storage
3. Скопируйте значение `access_token` или `token`
4. Вставьте в `.env`: `PARKING_TOKEN=ваш_токен`

Либо передавайте через заголовок: `Authorization: Bearer <token>`

## Запуск

```bash
# Локально
uvicorn api.app:app --host 0.0.0.0 --port 8127 --reload

# Через systemd (на VDS)
sudo cp tbilisi-parking-api.service /etc/systemd/system/
sudo systemctl enable --now tbilisi-parking-api
```

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/health` | Проверка токена и статус |
| `GET` | `/person` | Информация о пользователе |
| `GET` | `/vehicles` | Все машины |
| `POST` | `/vehicles` | Добавить машину |
| `DELETE` | `/vehicles/{id}` | Удалить машину |
| `GET` | `/parking/active` | Активные парковки |
| `POST` | `/parking/start` | Начать парковку |
| `POST` | `/parking/stop/{id}` | Остановить парковку |
| `GET` | `/parking/history` | История парковок |
| `GET` | `/places` | Все парковочные места |
| `GET` | `/places?search=...` | Поиск мест по адресу |
| `GET` | `/tariffs` | Тарифы и цены |
| `POST` | `/token` | Обновить токен |

### Примеры

```bash
# Поставить машину на парковку
curl -X POST http://localhost:8127/parking/start \
  -H "Content-Type: application/json" \
  -d '{"vehicleId": 1446810, "placeNo": "A1023", "type": "ONLY_PRICED_PARKING"}'

# Остановить
curl -X POST http://localhost:8127/parking/stop/41621974

# Найти место
curl "http://localhost:8127/places?search=gudiashvili"

# Список машин
curl http://localhost:8127/vehicles
```

## Swagger UI

При запущенном сервисе: http://localhost:8127/docs

## Архитектура

```
api/
├── __init__.py    # Экспорт моделей
├── app.py         # FastAPI приложение (эндпоинты)
├── client.py      # HTTP-клиент для municipal.gov.ge API
└── models.py      # Pydantic модели данных

scripts/
└── get_token.py   # Хелпер для получения токена

tests/             # TODO: тесты
```

## Технологии

- Python 3.11
- FastAPI + Uvicorn
- httpx (HTTP-клиент)
- Pydantic v2 (валидация)
- Systemd (автозапуск)
- Токен: Bearer JWT
- API base: `https://api.municipal.gov.ge`

## License

MIT
