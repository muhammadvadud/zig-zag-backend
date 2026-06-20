from modeltranslation.translator import TranslationOptions, register

from .models import FAQ, Banner, Category, Collection, Color, Product, Room, Style


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Style)
class StyleTranslationOptions(TranslationOptions):
    fields = ("name", "blurb")


@register(Room)
class RoomTranslationOptions(TranslationOptions):
    fields = ("name",)


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
