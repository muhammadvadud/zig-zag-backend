from django.db import migrations


def copy_to_base(apps, schema_editor):
    ServiceTariff = apps.get_model("services", "ServiceTariff")
    for obj in ServiceTariff.objects.all():
        obj.name = obj.name_uz
        old = obj.features
        if isinstance(old, dict):
            obj.features_uz = old.get("uz", [])
            obj.features_ru = old.get("ru", old.get("uz", []))
        else:
            obj.features_uz = old or []
            obj.features_ru = old or []
        obj.features = obj.features_uz
        obj.save(update_fields=["name", "features", "features_uz", "features_ru"])


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0002_servicetariff_features_ru_servicetariff_features_uz_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_to_base, migrations.RunPython.noop),
    ]
