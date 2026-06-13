from django.db import migrations

# Map each model to the (base_field, default_language_field) pairs whose
# existing data must seed the new modeltranslation base column.
FIELD_MAP = {
    "Category": [("name", "name_uz")],
    "Color": [("name", "name_uz")],
    "Product": [("name", "name_uz"), ("description", "description_uz")],
    "Collection": [("title", "title_uz")],
    "Banner": [("title", "title_uz")],
    "FAQ": [("question", "question_uz"), ("answer", "answer_uz")],
}


def copy_to_base(apps, schema_editor):
    for model_name, pairs in FIELD_MAP.items():
        Model = apps.get_model("catalog", model_name)
        for obj in Model.objects.all():
            for base, source in pairs:
                setattr(obj, base, getattr(obj, source))
            obj.save(update_fields=[base for base, _ in pairs])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_alter_category_options_banner_title_category_name_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_to_base, migrations.RunPython.noop),
    ]
