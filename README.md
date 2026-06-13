# ZIG ZAG — Backend

Premium pardalar onlayn do'koni uchun backend (Django + DRF). Katalog, savat,
buyurtmalar, xizmat tariflari, o'lchov so'rovlari, to'lovlar (Payme / Click),
AI yordamchi (chat) va AI rasm generatsiyasi — token nazorati bilan.

## Texnologiyalar

- Python 3.12, Django 5.2, Django REST Framework
- PostgreSQL 16, Redis 7
- Celery (asinxron vazifalar — AI rasm, va h.k.)
- JWT (SimpleJWT) + OTP (SMS) autentifikatsiya
- drf-spectacular (OpenAPI 3 / Swagger)

## Tezkor ishga tushirish (Docker)

```bash
cp .env.example .env        # va qiymatlarni to'ldiring
docker compose up --build
```

Servislar ko'tariladi: `db` (Postgres), `redis`, `web` (Gunicorn),
`worker` va `beat` (Celery). `web` avtomatik `migrate` va `collectstatic`
qiladi.

API: http://localhost:8000/api/v1/
Swagger: http://localhost:8000/api/docs/
Admin: http://localhost:8000/admin/

### Demo ma'lumotlar va admin foydalanuvchi

```bash
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py createsuperuser
```

## Lokal ishlab chiqish (Dockersiz)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# .env da POSTGRES_DB ni bo'sh qoldiring -> SQLite ishlatiladi
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

## Muhim sozlamalar (.env)

| O'zgaruvchi | Tavsif |
|-------------|--------|
| `DJANGO_DEBUG` | Productionda `False` |
| `POSTGRES_*` | Bo'sh bo'lsa SQLite ishlatiladi |
| `REDIS_URL` / `CELERY_*` | Kesh, throttle, navbat |
| `OTP_DEBUG_RETURN_CODE` | Dev'da OTP kodini javobda qaytaradi (prod'da `False`) |
| `AI_STUB_MODE` | API kalitsiz AI'ni offline stub bilan ishlatadi |
| `ANTHROPIC_API_KEY` | LLM kaliti (faqat backendda) |
| `PAYME_*` / `CLICK_*` | To'lov provayder kalitlari va IP allowlist |

## AI token nazorati

- LLM kaliti faqat backendda; frontend to'g'ridan-to'g'ri chaqirmaydi.
- Ko'p qatlamli cheklash: throttle (so'rov chastotasi), oylik token/rasm kvotasi
  (`AIUsageQuota`), kirish uzunligi limiti, `max_tokens`, kontekst oynasi
  (oxirgi N xabar), prompt-injection filtri, idempotency.
- Admin monitoring: `GET /api/v1/admin/ai/usage/`.

## Xavfsizlik

- IDOR himoyasi: shaxsiy resurslar `request.user` bo'yicha filtrlanadi +
  object-level permission.
- To'lov: webhook imzo/auth + IP allowlist, server tomonida summa tekshiruvi,
  idempotent tranzaksiyalar.
- OTP: hash holida saqlanadi, urinish limiti, cooldown, javobda kod yo'q.
- DRF throttling + Redis hisoblagichlar; prod uchun Nginx (`docker/nginx.conf`)
  va Cloudflare/WAF tavsiya etiladi.

## Loyiha tuzilishi

```
config/            # settings, urls, celery, wsgi/asgi
apps/
  common/          # BaseModel, throttle, permission, exception handler, audit
  accounts/        # User, OTP, Address, auth (OTP+JWT), profil
  catalog/         # Category, Product, Variant, Image, Review, Favorite, ...
  services/        # ServiceTariff (Smart/Lux/Premium)
  cart/            # Cart, CartItem (anonim + merge)
  orders/          # Order, OrderItem, MeasurementRequest, GiftCard
  payments/        # Payme (JSON-RPC) + Click webhooklari
  ai/              # AI chat, rasm generatsiya, kvota, provider abstraksiyasi
docker/            # entrypoint, nginx namunasi
```
