from modeltranslation.translator import TranslationOptions, register

from .models import FAQ, Banner, Category, Collection, Color, Product


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
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
    fields = ("title",)


@register(FAQ)
class FAQTranslationOptions(TranslationOptions):
    fields = ("question", "answer")
