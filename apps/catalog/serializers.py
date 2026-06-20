from rest_framework import serializers

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
    Room,
    Style,
)


class ImageUrlMixin:
    """Build absolute media URLs when a request is available in context.

    Translatable text fields (name/title/description/...) are resolved
    automatically by django-modeltranslation from the request's active
    language (set by LocaleMiddleware from the Accept-Language header).
    """

    def abs_url(self, image):
        if not image:
            return None
        request = self.context.get("request")
        url = image.url
        return request.build_absolute_uri(url) if request else url


class CategorySerializer(ImageUrlMixin, serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("slug", "name", "icon", "image", "sort_order", "products_count")

    def get_icon(self, obj):
        return self.abs_url(obj.icon)

    def get_image(self, obj):
        return self.abs_url(obj.image)


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ("id", "name", "hex")


class StyleSerializer(ImageUrlMixin, serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Style
        fields = ("slug", "name", "blurb", "image", "sort_order")

    def get_image(self, obj):
        return self.abs_url(obj.image)


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("slug", "name", "sort_order")


class ProductImageSerializer(ImageUrlMixin, serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "image", "is_main", "sort_order", "variant")

    def get_image(self, obj):
        return self.abs_url(obj.image)


class ProductVariantSerializer(serializers.ModelSerializer):
    color = ColorSerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ProductVariant
        fields = ("id", "sku", "color", "stock", "extra_price", "unit_price")


class ProductListSerializer(ImageUrlMixin, serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    main_image = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    colors_count = serializers.SerializerMethodField()
    styles = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)
    rooms = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

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
            "styles",
            "rooms",
            "reviews_count",
        )

    def get_main_image(self, obj):
        main = next((i for i in obj.images.all() if i.is_main), None) or next(iter(obj.images.all()), None)
        return self.abs_url(main.image) if main else None

    def get_colors(self, obj):
        return [{"name": v.color.name, "hex": v.color.hex} for v in obj.variants.all()]

    def get_colors_count(self, obj):
        return obj.variants.count()


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "description",
            "material",
            "price_per_m2",
            "views_count",
            "images",
            "variants",
        )


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


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "product", "created_at")


class CollectionSerializer(ImageUrlMixin, serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    products = ProductListSerializer(many=True, read_only=True)

    class Meta:
        model = Collection
        fields = ("slug", "title", "image", "products")

    def get_image(self, obj):
        return self.abs_url(obj.image)


class BannerSerializer(ImageUrlMixin, serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ("id", "title", "eyebrow", "subtitle", "cta", "image", "link")

    def get_image(self, obj):
        return self.abs_url(obj.image)


class AdminProductSerializer(serializers.ModelSerializer):
    """Full read/write product representation for staff management.

    Exposes the per-language fields explicitly so staff can edit each
    translation directly.
    """

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


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ("id", "question", "answer")
