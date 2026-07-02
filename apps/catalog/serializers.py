from uuid import uuid4

from django.utils.text import slugify
from rest_framework import serializers

from .models import (
    FAQ,
    Badge,
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


class BadgeSerializer(serializers.ModelSerializer):
    """Public nishon — front-da mahsulot ustida ko'rsatiladi."""

    class Meta:
        model = Badge
        fields = ("id", "name", "color")


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
        fields = ("id", "image", "is_main", "sort_order", "color")

    def get_image(self, obj):
        return self.abs_url(obj.image)


class ProductVariantSerializer(serializers.ModelSerializer):
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    label = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ("id", "name", "width_cm", "height_cm", "price", "unit_price", "is_active", "label")

    def get_label(self, obj):
        if obj.name:
            return obj.name
        if obj.width_cm and obj.height_cm:
            return f"{obj.width_cm}×{obj.height_cm} sm"
        return ""


class TailorSerializer(ImageUrlMixin, serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Tailor
        fields = ("id", "name", "initials", "specialty", "photo", "rating", "orders_count")

    def get_photo(self, obj):
        return self.abs_url(obj.photo)


class ProductListSerializer(ImageUrlMixin, serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    starting_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    main_image = serializers.SerializerMethodField()
    sizes_count = serializers.SerializerMethodField()
    styles = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)
    rooms = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)
    badges = BadgeSerializer(many=True, read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "slug",
            "name",
            "category",
            "starting_price",
            "discount_percent",
            "final_price",
            "is_new",
            "custom_only",
            "size_mode",
            "rating_avg",
            "main_image",
            "sizes_count",
            "material",
            "styles",
            "rooms",
            "badges",
            "reviews_count",
        )

    def get_main_image(self, obj):
        main = next((i for i in obj.images.all() if i.is_main), None) or next(iter(obj.images.all()), None)
        return self.abs_url(main.image) if main else None

    def get_sizes_count(self, obj):
        return obj.variants.filter(is_active=True).count()


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    colors = ColorSerializer(many=True, read_only=True)
    tailor = TailorSerializer(read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "description",
            "price_per_m2",
            "views_count",
            "images",
            "variants",
            "colors",
            "tailor",
        )


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    # Uchta baho ham majburiy (1-5).
    rating = serializers.IntegerField(min_value=1, max_value=5)
    rating_tailor = serializers.IntegerField(min_value=1, max_value=5)
    rating_service = serializers.IntegerField(min_value=1, max_value=5)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            "id",
            "rating",
            "rating_tailor",
            "rating_service",
            "comment",
            "user_name",
            "is_published",
            "is_mine",
            "created_at",
        )
        read_only_fields = ("id", "user_name", "is_published", "is_mine", "created_at")

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)


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
            "rating_tailor",
            "rating_service",
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
            "rating_tailor",
            "rating_service",
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
        fields = ("id", "image", "room", "room_name", "product", "tag", "is_tall")

    def get_image(self, obj):
        return self.abs_url(obj.image)


# ---------------------------------------------------------------------------
# Admin (write) serializers
# ---------------------------------------------------------------------------


class SlugAutoMixin:
    """Slug'ni to'liq orqa tarafda yaratadi: ``slugify(manba)-<pk>``.

    Admin slug kiritmaydi/ko'rmaydi — nomdan hosil qilinadi, oxiriga obyektning
    o'z id si qo'shiladi, shu bois slug har doim unikal. Mijoz yuborgan slug
    e'tiborga olinmaydi. Subclasslar ``slug_source`` (masalan "name" yoki "title")
    ni belgilaydi.
    """

    slug_source = "name"

    def _build_slug(self, instance):
        base = slugify(getattr(instance, self.slug_source, "") or "") or "item"
        base = base[:40].rstrip("-")  # SlugField(max_length=50) ichida id uchun joy qoldiramiz
        return f"{base}-{instance.pk}"

    def create(self, validated_data):
        validated_data.pop("slug", None)  # slug orqa tarafda yaratiladi
        # pk hali yo'q — vaqtinchalik unikal slug bilan yaratamiz, so'ng id bilan qayta yozamiz.
        validated_data["slug"] = f"tmp-{uuid4().hex[:12]}"
        instance = super().create(validated_data)
        instance.slug = self._build_slug(instance)
        instance.save(update_fields=["slug"])
        return instance

    def update(self, instance, validated_data):
        validated_data.pop("slug", None)  # slug orqa tarafda boshqariladi
        instance = super().update(instance, validated_data)
        new_slug = self._build_slug(instance)
        if instance.slug != new_slug:
            instance.slug = new_slug
            instance.save(update_fields=["slug"])
        return instance


class AdminColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ("id", "name", "hex")


class AdminProductVariantSerializer(serializers.ModelSerializer):
    """Tayyor o'lchamli variant (admin yozish/o'qish)."""
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ProductVariant
        fields = ("id", "name", "width_cm", "height_cm", "price", "unit_price", "is_active")


class AdminProductImageSerializer(ImageUrlMixin, serializers.ModelSerializer):
    """Mahsulot rasmi (admin yozish/o'qish)."""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "image_url", "image", "is_main", "sort_order", "color")
        extra_kwargs = {"image": {"write_only": True, "required": True}}

    def get_image_url(self, obj):
        return self.abs_url(obj.image)


class AdminProductSerializer(SlugAutoMixin, serializers.ModelSerializer):
    """Full read/write product representation for staff management.

    Slug bo'sh qoldirilsa name_uz dan avtomatik yaratiladi.
    """

    slug_source = "name_uz"

    # Narx variantlarda — bu faqat ro'yxat uchun "dan" narxi (eng arzon variant).
    starting_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    badges = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Badge.objects.all(), required=False
    )
    badges_detail = BadgeSerializer(many=True, read_only=True, source="badges")
    styles = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Style.objects.all(), required=False
    )
    rooms = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Room.objects.all(), required=False
    )
    colors = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Color.objects.all(), required=False
    )
    colors_detail = AdminColorSerializer(many=True, read_only=True, source="colors")

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
            "starting_price",
            "price_per_m2",
            "discount_percent",
            "is_active",
            "size_mode",
            "tailor",
            "badges",
            "badges_detail",
            "styles",
            "rooms",
            "colors",
            "colors_detail",
        )
        extra_kwargs = {
            "slug": {"read_only": True},  # slug orqa tarafda avtomatik (nom + id)
        }


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
            "slug": {"read_only": True},  # slug orqa tarafda avtomatik (nom + id)
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
            "slug": {"read_only": True},  # slug orqa tarafda avtomatik (nom + id)
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
            "slug": {"read_only": True},  # slug orqa tarafda avtomatik (nom + id)
        }


class AdminBadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ("id", "name_uz", "name_ru", "color", "sort_order", "is_active")


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
            "slug": {"read_only": True},  # slug orqa tarafda avtomatik (nom + id)
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
