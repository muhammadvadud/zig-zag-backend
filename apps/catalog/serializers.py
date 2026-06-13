from rest_framework import serializers

from apps.common.utils import current_language

from .models import (
    FAQ,
    Banner,
    Category,
    Collection,
    Color,
    Favorite,
    Product,
    ProductImage,
    ProductVariant,
    Review,
)


class LangMixin:
    def lang(self):
        request = self.context.get("request")
        return current_language(request) if request else "uz"

    def abs_url(self, image):
        if not image:
            return None
        request = self.context.get("request")
        url = image.url
        return request.build_absolute_uri(url) if request else url


class CategorySerializer(LangMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("slug", "name", "icon", "sort_order", "products_count")

    def get_name(self, obj):
        return obj.name(self.lang())

    def get_icon(self, obj):
        return self.abs_url(obj.icon)


class ColorSerializer(LangMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Color
        fields = ("id", "name", "hex")

    def get_name(self, obj):
        return obj.name(self.lang())


class ProductImageSerializer(LangMixin, serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "image", "is_main", "sort_order", "variant")

    def get_image(self, obj):
        return self.abs_url(obj.image)


class ProductVariantSerializer(LangMixin, serializers.ModelSerializer):
    color = ColorSerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ProductVariant
        fields = ("id", "sku", "color", "stock", "extra_price", "unit_price")


class ProductListSerializer(LangMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    main_image = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    colors_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "slug",
            "name",
            "category",
            "base_price",
            "discount_percent",
            "final_price",
            "is_new",
            "rating_avg",
            "stock",
            "main_image",
            "colors",
            "colors_count",
        )

    def get_name(self, obj):
        return obj.name(self.lang())

    def get_main_image(self, obj):
        main = next((i for i in obj.images.all() if i.is_main), None) or next(iter(obj.images.all()), None)
        return self.abs_url(main.image) if main else None

    def get_colors(self, obj):
        return [
            {"name": v.color.name(self.lang()), "hex": v.color.hex}
            for v in obj.variants.all()
        ]

    def get_colors_count(self, obj):
        return obj.variants.count()


class ProductDetailSerializer(ProductListSerializer):
    description = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews_count = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "description",
            "material",
            "price_per_m2",
            "views_count",
            "images",
            "variants",
            "reviews_count",
        )

    def get_description(self, obj):
        return obj.description(self.lang())

    def get_reviews_count(self, obj):
        return obj.reviews.filter(is_published=True).count()


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "rating", "comment", "user_name", "created_at")
        read_only_fields = ("id", "user_name", "created_at")

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Baho 1 dan 5 gacha bo'lishi kerak.")
        return value


class FavoriteSerializer(LangMixin, serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "product", "created_at")


class CollectionSerializer(LangMixin, serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    products = ProductListSerializer(many=True, read_only=True)

    class Meta:
        model = Collection
        fields = ("slug", "title", "image", "products")

    def get_title(self, obj):
        return obj.title(self.lang())

    def get_image(self, obj):
        return self.abs_url(obj.image)


class BannerSerializer(LangMixin, serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ("id", "title", "image", "link")

    def get_title(self, obj):
        return obj.title(self.lang())

    def get_image(self, obj):
        return self.abs_url(obj.image)


class AdminProductSerializer(serializers.ModelSerializer):
    """Full read/write product representation for staff management."""

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "slug",
            "name_uz",
            "name_ru",
            "description_uz",
            "description_ru",
            "material",
            "base_price",
            "price_per_m2",
            "discount_percent",
            "is_new",
            "is_active",
            "stock",
        )


class FAQSerializer(LangMixin, serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        fields = ("id", "question", "answer")

    def get_question(self, obj):
        return obj.question_ru if self.lang() == "ru" else obj.question_uz

    def get_answer(self, obj):
        return obj.answer_ru if self.lang() == "ru" else obj.answer_uz
