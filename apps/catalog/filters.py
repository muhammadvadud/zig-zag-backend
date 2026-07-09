import django_filters as filters
from django.db.models import Max, Min, Q

from .models import Product

_LIVE_VARIANT = Q(variants__is_deleted=False)  # o'chirilgan variantlar narxga ta'sir qilmaydi


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category__slug")
    # Rang endi mahsulot darajasida (Product.colors), variantda emas.
    color = filters.CharFilter(field_name="colors__name_uz", lookup_expr="iexact")
    # Mato/material endi alohida model (M2M) — slug bo'yicha filtrlaymiz.
    material = filters.CharFilter(field_name="materials__slug", lookup_expr="iexact")
    is_new = filters.BooleanFilter(field_name="is_new")
    # Narx variantlarda — mahsulotning eng arzon/eng qimmat variant narxi bo'yicha filtrlaymiz.
    min_price = filters.NumberFilter(method="filter_min_price")
    max_price = filters.NumberFilter(method="filter_max_price")

    class Meta:
        model = Product
        fields = ["category", "color", "material", "is_new", "min_price", "max_price"]

    def filter_min_price(self, queryset, name, value):
        return queryset.annotate(_max_price=Max("variants__price", filter=_LIVE_VARIANT)).filter(_max_price__gte=value)

    def filter_max_price(self, queryset, name, value):
        return queryset.annotate(_min_price=Min("variants__price", filter=_LIVE_VARIANT)).filter(_min_price__lte=value)
