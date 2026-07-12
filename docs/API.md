# Turtle Cruise API

## Swagger UI

После запуска сервера:

- **Swagger UI:** http://127.0.0.1:8000/api/docs/
- **OpenAPI schema:** http://127.0.0.1:8000/api/schema/

## Public endpoints

| Method | Path | Описание |
|--------|------|----------|
| GET | `/api/v1/cruises/` | Список круизов и расписаний |
| GET | `/api/v1/cruises/{code}/availability/?date=YYYY-MM-DD` | Доступность + `time_label` |
| POST | `/api/v1/bookings/hold/` | Создать бронь (pending_payment) |
| GET | `/api/v1/bookings/{public_id}/` | Детали брони + `cruise_time` |
| GET | `/api/v1/bookings/{public_id}/trace/` | **Полная цепочка логов брони** |
| POST | `/api/v1/bookings/{public_id}/cancel/` | Отменить pending бронь |
| POST | `/api/v1/payments/stripe/payment-intent/` | Stripe PaymentIntent |
| POST | `/api/v1/payments/stripe/confirm/` | Fallback confirm (не источник истины) |
| POST | `/api/v1/payments/stripe/webhook/` | Stripe webhook |
| POST | `/api/v1/audit/events/` | Трекинг шага пользователя |
| POST | `/wp-admin/admin-ajax.php` | WordPress compatibility layer |

## WordPress compatibility actions

| action | Описание |
|--------|----------|
| `tc_get_availability` | Доступность мест |
| `tc_create_booking` | Создать бронь |
| `tc_create_payment_intent` | PaymentIntent |
| `tc_confirm_payment` / `tc_verify_payment` | Fallback confirm |
| `tc_cancel_booking` | Отмена |
| `tc_track_event` | Journey event |

## Hold request example

```json
POST /api/v1/bookings/hold/
{
  "cruise_code": "morning",
  "cruise_date": "2026-07-15",
  "adults_count": 2,
  "children_count": 0,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+35799123456",
  "session_id": "uuid-from-frontend"
}
```

## Trace response example

```json
GET /api/v1/bookings/ABC123/trace/
{
  "found": true,
  "booking": { "public_id": "ABC123", "status": "confirmed", ... },
  "timeline": [
    { "type": "operation", "action": "hold_created", "at": "..." },
    { "type": "operation", "action": "payment_intent_created", "at": "..." },
    { "type": "operation", "action": "webhook_received", "at": "..." },
    { "type": "operation", "action": "booking_confirmed", "at": "..." },
    { "type": "email", "template_code": "booking_customer", "status": "sent", "at": "..." },
    { "type": "sms", "status": "sent", "at": "..." }
  ],
  "summary": { "operations": 6, "emails": 2, "sms": 1, ... }
}
```

Подробнее о цепочке и логах: [BOOKING_CHAIN.md](./BOOKING_CHAIN.md)
