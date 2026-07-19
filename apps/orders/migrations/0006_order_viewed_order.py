from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_order_delivery_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="viewed_order",
            field=models.BooleanField(default=False),
        ),
    ]
