from modeltranslation.translator import TranslationOptions, register

from .models import (
    FAQ,
    Badge,
    Banner,
    Category,
    Collection,
    Color,
    HeroContent,
    Material,
    Product,
    Room,
    Style,
    Tailor,
    Testimonial,
    Work,
)


@register(Badge)
class BadgeTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Style)
class StyleTranslationOptions(TranslationOptions):
    fields = ("name", "blurb")


@register(Room)
class RoomTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Material)
class MaterialTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(Tailor)
class TailorTranslationOptions(TranslationOptions):
    fields = ("name", "specialty")


@register(Color)
class ColorTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Product)
class ProductTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(Collection)
class CollectionTranslationOptions(TranslationOptions):
    fields = ("title",)


@register(Banner)
class BannerTranslationOptions(TranslationOptions):
    fields = ("title", "eyebrow", "subtitle", "cta")


@register(FAQ)
class FAQTranslationOptions(TranslationOptions):
    fields = ("question", "answer")


@register(HeroContent)
class HeroContentTranslationOptions(TranslationOptions):
    fields = (
        "eyebrow",
        "title",
        "title_italic",
        "description",
        "stat1_label",
        "stat2_label",
        "stat3_label",
    )


@register(Testimonial)
class TestimonialTranslationOptions(TranslationOptions):
    fields = ("location", "text", "date_label")


@register(Work)
class WorkTranslationOptions(TranslationOptions):
    fields = ("tag",)
