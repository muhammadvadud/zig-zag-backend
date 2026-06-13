from modeltranslation.translator import TranslationOptions, register

from .models import ServiceTariff


@register(ServiceTariff)
class ServiceTariffTranslationOptions(TranslationOptions):
    fields = ("name", "features")
