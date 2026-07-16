from django.db import migrations
from django.utils.text import slugify


def forwards(apps, schema_editor):
    """Eski Product.material (matn) qiymatlarini Material obyektlariga ko'chirib,
    mahsulotlarga M2M orqali bog'laymiz."""
    Product = apps.get_model("catalog", "Product")
    Material = apps.get_model("catalog", "Material")

    cache = {}
    order = 0
    for product in Product.objects.exclude(material="").exclude(material__isnull=True):
        value = (product.material or "").strip()
        if not value:
            continue
        key = value.lower()
        material = cache.get(key)
        if material is None:
            slug = slugify(value) or f"material-{order}"
            material, created = Material.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": value,
                    "name_uz": value,
                    "name_ru": value,
                    "sort_order": order,
                },
            )
            cache[key] = material
            if created:
                order += 1
        product.materials.add(material)


def backwards(apps, schema_editor):
    """Ortga: birinchi biriktirilgan material nomini matn maydoniga qaytaramiz."""
    Product = apps.get_model("catalog", "Product")
    for product in Product.objects.all():
        first = product.materials.first()
        if first:
            product.material = first.name
            product.save(update_fields=["material"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0019_material_product_materials"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
