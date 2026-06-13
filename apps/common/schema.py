"""Custom OpenAPI schema that groups endpoints by feature instead of /v1/.

drf-spectacular tags operations by the first URL segment by default, which
puts everything under one "api/v1" group. Here we derive a readable tag from
the path so Swagger shows clear, task-based sections.
"""

from drf_spectacular.openapi import AutoSchema

API_PREFIX = "/api/v1/"

# Order matters: more specific prefixes (admin/, ai/images) come first.
_RULES = (
    ("admin/", "Admin"),
    ("auth/", "Auth"),
    ("profile", "Profil"),
    ("favorites", "Sevimlilar"),
    ("categories", "Katalog"),
    ("products", "Katalog"),
    ("collections", "Katalog"),
    ("banners", "Katalog"),
    ("faq", "Katalog"),
    ("tariffs", "Tariflar"),
    ("cart", "Savat"),
    ("orders", "Buyurtmalar"),
    ("measurements", "Buyurtmalar"),
    ("payments", "To'lovlar"),
    ("ai/images", "AI rasm"),
    ("ai/", "AI yordamchi"),
    ("health", "Tizim"),
)


class TaggedAutoSchema(AutoSchema):
    def get_tags(self):
        path = self.path or ""
        idx = path.find(API_PREFIX)
        rest = path[idx + len(API_PREFIX):] if idx >= 0 else path.lstrip("/")
        for prefix, tag in _RULES:
            if rest.startswith(prefix):
                return [tag]
        return ["API"]
