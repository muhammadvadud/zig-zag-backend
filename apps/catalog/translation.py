from modeltranslation.translator import TranslationOptions, register

from .models import FAQ, Banner, Category, Collection, Color, HeroContent, Product, Room, Style, Tailor


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Style)
class StyleTranslationOptions(TranslationOptions):
    fields = ("name", "blurb")


@register(Room)
class RoomTranslationOptions(TranslationOptions):
    fields = ("name",)


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
        "stat1_value",
        "stat1_label",
        "stat2_value",
        "stat2_label",
        "stat3_value",
        "stat3_label",
    )
