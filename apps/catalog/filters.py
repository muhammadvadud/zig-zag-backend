import django_filters as filters

from .models import Product


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category__slug")
    color = filters.CharFilter(field_name="variants__color__name_uz", lookup_expr="iexact")
    material = filters.CharFilter(field_name="material", lookup_expr="iexact")
    is_new = filters.BooleanFilter(field_name="is_new")
    min_price = filters.NumberFilter(field_name="base_price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="base_price", lookup_expr="lte")
    in_stock = filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = ["category", "color", "material", "is_new", "min_price", "max_price", "in_stock"]

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__gt=0)
        return queryset
