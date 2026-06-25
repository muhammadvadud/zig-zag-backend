from django.utils.text import slugify
from rest_framework import serializers

from .models import (
    FAQ,
    Banner,
    Category,
    Collection,
    Color,
    Favorite,
    HeroContent,
    Product,
    ProductImage,
    ProductVariant,
    Review,
    Room,
    Style,
    Tailor,
    Testimonial,
    Work,
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


class TailorSerializer(ImageUrlMixin, serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Tailor
        fields = ("id", "name", "initials", "specialty", "photo", "rating", "orders_count")

    def get_photo(self, obj):
        return self.abs_url(obj.photo)


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
            "material",
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
    tailor = TailorSerializer(read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "description",
            "price_per_m2",
            "views_count",
            "images",
            "variants",
            "tailor",
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
            "tailor",
        )


class AdminTailorSerializer(ImageUrlMixin, serializers.ModelSerializer):
    """Full read/write tailor representation for staff management."""

    photo = serializers.SerializerMethodField()

    class Meta:
        model = Tailor
        fields = (
            "id",
            "name_uz",
            "name_ru",
            "initials",
            "specialty_uz",
            "specialty_ru",
            "rating",
            "orders_count",
            "sort_order",
            "is_active",
            "photo",
        )

    def get_photo(self, obj):
        return self.abs_url(obj.photo)


class AdminReviewSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "product",
            "product_slug",
            "user_name",
            "rating",
            "comment",
            "is_published",
            "created_at",
        )
        read_only_fields = (
            "id",
            "product",
            "product_slug",
            "user_name",
            "rating",
            "comment",
            "created_at",
        )


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ("id", "question", "answer")


class HeroContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroContent
        fields = (
            "id",
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


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = (
            "id",
            "name",
            "location",
            "text",
            "date_label",
            "stars",
            "initials",
            "color",
        )


class WorkSerializer(ImageUrlMixin, serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    room = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    room_name = serializers.CharField(source="room.name", read_only=True, default="")

    class Meta:
        model = Work
        fields = ("id", "image", "room", "room_name", "tag", "is_tall")

    def get_image(self, obj):
        return self.abs_url(obj.image)


# ---------------------------------------------------------------------------
# Admin (write) serializers
# ---------------------------------------------------------------------------


class SlugAutoMixin:
    """Auto-generate a unique slug from ``slug_source`` when slug is blank.

    Subclasses set ``slug_source`` to the field name to slugify (e.g. "name"
    or "title"). Collisions are resolved by appending -2, -3, ...
    """

    slug_source = "name"

    def _unique_slug(self, base, instance=None):
        base = base or "item"
        candidate = base
        model = self.Meta.model
        n = 2
        qs = model.objects.all()
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        while qs.filter(slug=candidate).exists():
            candidate = f"{base}-{n}"
            n += 1
        return candidate

    def create(self, validated_data):
        if not validated_data.get("slug"):
            base = slugify(validated_data.get(self.slug_source, "") or "")
            validated_data["slug"] = self._unique_slug(base)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Blank slug on edit: keep the existing one (don't overwrite with "").
        if "slug" in validated_data and not validated_data["slug"]:
            validated_data.pop("slug")
        return super().update(instance, validated_data)


class AdminCategorySerializer(ImageUrlMixin, SlugAutoMixin, serializers.ModelSerializer):
    slug_source = "name"

    class Meta:
        model = Category
        fields = (
            "id",
            "slug",
            "name",
            "icon",
            "image",
            "sort_order",
            "is_active",
        )
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "icon": {"required": False},
            "image": {"required": False},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["icon"] = self.abs_url(instance.icon)
        data["image"] = self.abs_url(instance.image)
        return data


class AdminStyleSerializer(ImageUrlMixin, SlugAutoMixin, serializers.ModelSerializer):
    slug_source = "name"

    class Meta:
        model = Style
        fields = (
            "id",
            "slug",
            "name",
            "blurb",
            "image",
            "sort_order",
            "is_active",
        )
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "image": {"required": False},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["image"] = self.abs_url(instance.image)
        return data


class AdminRoomSerializer(SlugAutoMixin, serializers.ModelSerializer):
    slug_source = "name"

    class Meta:
        model = Room
        fields = (
            "id",
            "slug",
            "name",
            "sort_order",
            "is_active",
        )
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }


class AdminColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ("id", "name", "hex")


class AdminCollectionSerializer(ImageUrlMixin, SlugAutoMixin, serializers.ModelSerializer):
    slug_source = "title"
    products = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Product.objects.all(), required=False
    )

    class Meta:
        model = Collection
        fields = (
            "id",
            "slug",
            "title",
            "image",
            "products",
            "sort_order",
            "is_active",
        )
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "image": {"required": False},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["image"] = self.abs_url(instance.image)
        return data


class AdminBannerSerializer(ImageUrlMixin, serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "eyebrow",
            "subtitle",
            "cta",
            "image",
            "link",
            "sort_order",
            "is_active",
        )
        extra_kwargs = {
            "image": {"required": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["image"] = self.abs_url(instance.image)
        return data


class AdminFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ("id", "question", "answer", "sort_order", "is_active")


class AdminHeroContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroContent
        fields = (
            "id",
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
            "sort_order",
            "is_active",
        )
