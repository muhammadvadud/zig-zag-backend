from decimal import Decimal

from django.db import migrations, models


def populate_variant_price(apps, schema_editor):
    """Har bir variant narxini eski base_price + extra_price dan to'ldiramiz."""
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    for v in ProductVariant.objects.select_related("product").all():
        base = v.product.base_price or Decimal("0")
        v.price = base + (v.extra_price or Decimal("0"))
        v.save(update_fields=["price"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0015_product_size_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.RunPython(populate_variant_price, noop),
        migrations.RemoveField(model_name="product", name="base_price"),
        migrations.RemoveField(model_name="productvariant", name="extra_price"),
        migrations.AlterModelOptions(
            name="productvariant",
            options={"ordering": ["price", "width_cm", "height_cm", "id"]},
        ),
    ]
