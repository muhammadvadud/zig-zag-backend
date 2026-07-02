from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0016_variant_price_drop_base_price"),
    ]

    operations = [
        migrations.RemoveField(model_name="product", name="stock"),
    ]
