# ZigZag — Admin panel dizayni va statistikasi

> Bu hujjat admin panel dizaynini chizish uchun. Hozirgi backend (Django + Unfold)
> da qaysi bo'limlar, maydonlar va statistikalar bor/bo'lishi kerakligini batafsil
> yozadi. Manba: `apps/*/models.py`, `apps/*/admin.py`, `config/settings.py`.

Texnologiya: **Django admin + `django-unfold`** (zamonaviy tema). Chap tomonda
guruhlangan yon menyu (sidebar), tepada qidiruv. Til: uz/ru (modeltranslation —
tarjima qilinadigan maydonlar har biri uchun ikkita tab: «uz» va «ru»).

---

## 1. Bosh sahifa — Dashboard (statistika)

> ⚠️ **Holat:** hozircha alohida statistika sahifasi YO'Q. Quyidagilar mavjud
> modellardan hisoblab chiqilishi mumkin — ya'ni dizayn shu ko'rinishda bo'lsin,
> backendda esa shu metrikalar uchun API yoziladi (4-bo'limga qarang). Bu yerda
> har bir raqamning aniq manbasi ko'rsatilgan.

### 1.1. Yuqori qator — KPI kartalar (kattaroq raqamlar)

| Karta | Nimani ko'rsatadi | Manba (qanday hisoblanadi) |
|-------|-------------------|----------------------------|
| **Bugungi savdo** | Bugun to'langan buyurtmalar summasi | `Order` da `payment_status="paid"` va `created_at=bugun` → `Sum(total)` |
| **Oylik savdo** | Shu oydagi tushum | `Order(payment_status="paid", shu oy)` → `Sum(total)` |
| **Buyurtmalar soni** | Bugun/oy bo'yicha | `Order.count()` (sana filtri bilan) |
| **O'rtacha chek** | Bitta buyurtma o'rtacha summasi | `Order(paid)` → `Avg(total)` |
| **Yangi mijozlar** | Shu oyda ro'yxatdan o'tganlar | `User(role="customer", date_joined=shu oy)` → `count()` |
| **Kutilayotgan buyurtma** | Diqqat talab qiladiganlar | `Order(status in [pending, processing, measuring, sewing])` → `count()` |
| **O'lchov so'rovlari** | Yangi so'rovlar | `MeasurementRequest(status="requested")` → `count()` |
| **Konversiya** | Savatdan buyurtmagacha | `Order.count() / Cart.count()` (taxminiy) |

Har bir kartada: katta raqam + kichik «o'tgan davrga nisbatan %» (masalan ▲ 12%).

### 1.2. Grafiklar

- **Savdo dinamikasi (chiziqli grafik):** oxirgi 30 kun — har kuni `Sum(total)`
  (`Order`, `payment_status="paid"`, kun bo'yicha guruhlash).
- **Buyurtmalar holati (doiraviy/donut):** `Order.status` bo'yicha taqsimot
  (pending / processing / sewing / completed / cancelled ...).
- **To'lov usullari (bar):** `Payment.provider` bo'yicha (`payme` vs `click`) summa.
- **Top mahsulotlar (gorizontal bar):** eng ko'p sotilganlar —
  `OrderItem` → `variant__product` bo'yicha `Sum(quantity)`.
- **Top kategoriyalar:** `OrderItem` → `product.category` bo'yicha tushum.

### 1.3. Pastki ro'yxatlar (jadval ko'rinishida)

- **Oxirgi buyurtmalar** (10 ta): raqam, mijoz, holat, summa, sana.
- **Yangi o'lchov so'rovlari:** mijoz, sana, vaqt oralig'i, holat.
- **Kam qolgan mahsulotlar (stock past):** `Product`/`ProductVariant.stock < 10`.
- **Yangi sharhlar (moderatsiya kutyapti):** `Review(is_published=False)`.

---

## 2. Yon menyu (sidebar) bo'limlari

Hozir `config/settings.py` dagi `UNFOLD["SIDEBAR"]["navigation"]` da quyidagi
guruhlar bor. Har bir element — bitta model jadvali.

```
FOYDALANUVCHILAR
  • Foydalanuvchilar      (accounts.User)
  • Manzillar             (accounts.Address)
  • OTP kodlar            (accounts.OTPCode)

KATALOG
  • Kategoriyalar         (catalog.Category)
  • Uslublar              (catalog.Style)
  • Xonalar               (catalog.Room)
  • Chevarlar  ⟵ YANGI    (catalog.Tailor)
  • Mahsulotlar           (catalog.Product)
  • Variantlar            (catalog.ProductVariant)
  • Rasmlar               (catalog.ProductImage)
  • Ranglar               (catalog.Color)
  • Sharhlar              (catalog.Review)
  • Sevimlilar            (catalog.Favorite)
  • Kolleksiyalar         (catalog.Collection)
  • Bannerlar             (catalog.Banner)
  • Hero matnlari ⟵ YANGI (catalog.HeroContent)
  • FAQ                   (catalog.FAQ)

SAVDO
  • Tariflar              (services.ServiceTariff)
  • Savatlar              (cart.Cart)
  • Buyurtmalar           (orders.Order)
  • O'lchov so'rovlari    (orders.MeasurementRequest)
  • Sovg'a kartalari      (orders.GiftCard)
  • To'lovlar             (payments.Payment)

AI
  • Suhbatlar             (ai.AIConversation)
  • Rasm generatsiya      (ai.AIImageGeneration)
  • Kvota                 (ai.AIUsageQuota)

TIZIM
  • Audit jurnali         (common.AuditLog)
```

---

## 3. Har bir bo'lim batafsil (maydonlar)

### 3.1. Foydalanuvchilar — `accounts.User`
- **Maydonlar:** `phone` (unikal, login), `full_name`, `email`, `role`
  (customer / manager / admin), `is_active`, `is_phone_verified`, `language`
  (uz/ru), `date_joined`, `ai_quota_plan` (tarifga bog'liq AI kvotasi).
- **Ro'yxat ustunlari:** telefon, ism, rol, tasdiqlangan?, faol?.
- **Filtr:** rol, faol, telefon tasdiqlangan.
- **Dizayn uchun:** profil kartasi (avatar/initial, telefon, rol beji), buyurtmalar
  tarixiga havola.

### 3.2. Manzillar — `accounts.Address`
- `user`, `region`, `city`, `street`, `home`, `landmark`, `is_default`.

### 3.3. OTP kodlar — `accounts.OTPCode`
- `phone`, `purpose` (login/register), `attempts`, `expires_at`, `is_used`.
- Faqat o'qish uchun / xavfsizlik monitoringi.

### 3.4. Kategoriyalar — `catalog.Category`
- `slug`, `name` (uz/ru), `icon`, `image`, `sort_order`, `is_active`.

### 3.5. Uslublar — `catalog.Style`
- `slug`, `name` (uz/ru), `blurb` (uz/ru), `image`, `sort_order`, `is_active`.

### 3.6. Xonalar — `catalog.Room`
- `slug`, `name` (uz/ru), `sort_order`, `is_active`.

### 3.7. Chevarlar — `catalog.Tailor`  ⟵ **YANGI**
- **Maydonlar:** `name` (uz/ru), `initials` (avatar uchun, masalan «DY»),
  `specialty` (uz/ru — masalan «Linen · Sheer»), `photo` (rasm, ixtiyoriy),
  `rating` (0–5, masalan 4.9), `orders_count` (bajargan buyurtmalari soni),
  `sort_order`, `is_active`.
- **Ro'yxat ustunlari:** ism, mutaxassislik, reyting, buyurtmalar, faol?.
- **Bog'lanish:** har bir `Product` ga bitta chevar biriktiriladi
  (`Product.tailor`). Mahsulot sahifasida «Chevar usta» bloki shu ma'lumotni
  ko'rsatadi.
- **Dizayn uchun:** dumaloq avatar (rasm yoki initials), reyting yulduzchasi,
  buyurtmalar soni.

### 3.8. Mahsulotlar — `catalog.Product`
- **Maydonlar:** `slug`, `name` (uz/ru), `description` (uz/ru), `category`,
  `material`, `base_price`, `price_per_m2`, `discount_percent`, `is_new`,
  `is_active`, `stock`, `rating_avg`, `views_count`, `styles` (M2M),
  `rooms` (M2M), **`tailor`** (FK ⟵ yangi).
- **Ichki (inline) tahrirlash:** Variantlar + Rasmlar shu sahifada.
- **Ro'yxat ustunlari:** slug, nomi, kategoriya, **chevar**, narx, chegirma, stok,
  yangi?, faol?.
- **Filtr:** kategoriya, **chevar**, yangi, faol.
- **Dizayn uchun:** mahsulot kartasi — rasm, narx/chegirma, stok indikatori,
  chevar biriktirish (autocomplete dropdown).

### 3.9. Variantlar — `catalog.ProductVariant`
- `product`, `color`, `sku` (unikal), `stock`, `extra_price`.

### 3.10. Rasmlar — `catalog.ProductImage`
- `product`, `variant` (ixtiyoriy), `image`, `is_main`, `sort_order`.

### 3.11. Ranglar — `catalog.Color`
- `name` (uz/ru), `hex` (#RRGGBB). Dizayn: rang doirasi ko'rsatilsin.

### 3.12. Sharhlar — `catalog.Review`
- `product`, `user`, `order`, `rating` (1–5), `comment`, `is_published`.
- **Amal:** «Tanlangan sharhlarni e'lon qilish» (moderatsiya). Faqat
  `is_published=True` bo'lganlari saytda ko'rinadi va reytingga ta'sir qiladi.

### 3.13. Sevimlilar — `catalog.Favorite`
- `user`, `product`. (Statistika uchun — qaysi mahsulotlar ko'p yoqtirilgan.)

### 3.14. Kolleksiyalar — `catalog.Collection`
- `slug`, `title` (uz/ru), `image`, `products` (M2M), `sort_order`, `is_active`.

### 3.15. Bannerlar — `catalog.Banner`
- `title`/`eyebrow`/`subtitle`/`cta` (uz/ru), `image`, `link`, `sort_order`,
  `is_active`. Bosh sahifa karuseli.

### 3.16. Hero matnlari — `catalog.HeroContent`  ⟵ **YANGI**
- `eyebrow`, `title`, `title_italic`, `description` (uz/ru) + 3 ta statistika
  (`statN_value` / `statN_label`, uz/ru). Bosh sahifadagi banner yonidagi blok.
  Bitta faol yozuv ishlatiladi.

### 3.17. FAQ — `catalog.FAQ`
- `question` (uz/ru), `answer` (uz/ru), `sort_order`, `is_active`.

### 3.18. Tariflar — `services.ServiceTariff`
- `code`, `name` (uz/ru), `price`, `price_per_m2`, `is_popular`, `features`
  (ro'yxat), `sort_order`, `is_active`. O'lchov/tikuv xizmati narxlari.

### 3.19. Savatlar — `cart.Cart` / `cart.CartItem`
- `Cart`: `user` yoki `session_key` (mehmon). `CartItem`: `variant`, `quantity`,
  `width_cm`, `height_cm`, `service_tariff`. (Tashlab ketilgan savatlar
  statistikasi uchun.)

### 3.20. Buyurtmalar — `orders.Order` / `orders.OrderItem`
- **`Order`:** `order_number`, `user`, `status` (pending / paid / processing /
  measuring / sewing / shipped / completed / cancelled / refunded), `address`,
  `subtotal`, `discount`, `delivery_fee`, `total`, `payment_status`
  (unpaid / paid / failed / refunded), `payment_provider`, `comment`.
- **`OrderItem`:** `order`, `variant`, `product_name_snapshot`, `unit_price`,
  `quantity`, `width_cm`, `height_cm`, `service_tariff`, `line_total`.
- **Ro'yxat ustunlari:** raqam, mijoz, holat, to'lov holati, summa, sana.
- **Filtr:** holat, to'lov holati, provayder.
- **Dizayn uchun:** holat bo'yicha rangli bejlar (status timeline), buyurtma
  tafsiloti (mahsulotlar, o'lchov, summa breakdown).

### 3.21. O'lchov so'rovlari — `orders.MeasurementRequest`
- `user`, `order`, `address`, `preferred_date`, `time_slot`, `status`
  (requested / ...), `note`. Uyga o'lchovga chiqish so'rovlari.

### 3.22. Sovg'a kartalari — `orders.GiftCard`
- `code`, `balance`, `owner`, `is_active`.

### 3.23. To'lovlar — `payments.Payment`
- `order`, `provider` (payme / click), `provider_transaction_id`, `amount`,
  `state` (1=yaratilgan, 2=to'langan, -1/-2=bekor), `paid_at`, `cancelled_at`.

### 3.24. AI — `ai.*`
- **AIConversation:** `user`/`session_key`, `title`, `is_archived`.
- **AIMessage:** `conversation`, `role` (user/assistant), `content`,
  `input_tokens`, `output_tokens`, `model`, `latency_ms`. → AI xarajati/token
  statistikasi.
- **AIImageGeneration:** `user`, `product`, `prompt`, `status`
  (queued/.../done), `result_image`, `cost_credits`. → AI rasm generatsiya soni.
- **AIUsageQuota:** `user`, `period` («2026-06»), `tokens_used`/`token_limit`,
  `images_used`/`image_limit`, `messages_used`. → kvota nazorati.

### 3.25. Audit jurnali — `common.AuditLog`
- `actor`, `action`, `target_type`, `target_id`, `meta`, `ip`, `created_at`.
  Kim qachon nima qilgani (xavfsizlik jurnali).

---

## 4. Statistika uchun tavsiya etilgan API'lar (hozircha yo'q — yoziladi)

Dashboard uchun maxsus endpointlar kerak. Tavsiya: `apps/common` yoki yangi
`apps/analytics` ichida, faqat `is_staff` uchun. Hammasi mavjud modellardan
hisoblanadi (yangi jadval shart emas, lekin og'ir hisob-kitoblar uchun keshlash
yoki kunlik yig'ma `DailyStat` jadvali qo'shilishi mumkin).

| Endpoint | Qaytaradi | Manba modellar |
|----------|-----------|----------------|
| `GET /admin/stats/overview/` | KPI kartalar (bugun/oy savdo, buyurtma soni, o'rtacha chek, yangi mijoz) | `Order`, `User` |
| `GET /admin/stats/sales/?days=30` | Kunlik savdo grafigi | `Order(paid)` kun bo'yicha `Sum(total)` |
| `GET /admin/stats/orders-by-status/` | Holatlar taqsimoti (donut) | `Order` → `Count` group by `status` |
| `GET /admin/stats/top-products/?limit=10` | Top sotilgan mahsulotlar | `OrderItem` → `Sum(quantity)` group by mahsulot |
| `GET /admin/stats/top-categories/` | Kategoriya bo'yicha tushum | `OrderItem` → kategoriya |
| `GET /admin/stats/payments/` | Provayder bo'yicha to'lovlar | `Payment` → `Sum(amount)` group by `provider` |
| `GET /admin/stats/ai-usage/?period=2026-06` | AI token/rasm sarfi | `AIMessage`, `AIImageGeneration`, `AIUsageQuota` |
| `GET /admin/stats/low-stock/` | Kam qolgan mahsulotlar | `ProductVariant(stock < N)` |

**Eslatma — kunlik yig'ma model (ixtiyoriy, performans uchun):**
Agar buyurtmalar ko'paysa, har safar `Sum` qilish o'rniga kunlik snapshot
saqlash mumkin:

```
DailyStat(date, orders_count, revenue, new_users, ai_tokens, ...)
```

Buni Celery (`apps/*/tasks.py` allaqachon bor) har kuni yarim tunda to'ldiradi.
Hozircha bu shart emas — to'g'ridan-to'g'ri aggregatsiya yetarli.

---

## 5. Dizaynerga qisqa eslatmalar

- **Ranglar:** sayt brendi — navy `#1a2a4a` (asosiy/ink), gold `#c9a769` (accent),
  cream `#f6f1e7` (fon). Admin ham shu ohangda bo'lsa chiroyli (Unfold rang
  sozlamasi `config/settings.py` `UNFOLD["COLORS"]` orqali).
- **Til:** har bir matnli maydon ikki tilda (uz/ru) — tab yoki yonma-yon.
- **Holatlar:** buyurtma/to'lov holatlari rangli bej (yashil=to'langan,
  sariq=kutilmoqda, qizil=bekor).
- **Birlamchi ekran:** login'dan keyin Dashboard (1-bo'lim) ochilsin.
- **Yangi qo'shilganlar:** «Chevarlar» va «Hero matnlari» bo'limlari — ularni
  ham boshqa bo'limlar uslubida chizish kerak.
