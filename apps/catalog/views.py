from django.db.models import Count, F, Q
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsStaffRole
from apps.orders.models import OrderItem

from .filters import ProductFilter
from .models import (
    FAQ,
    Banner,
    Category,
    Collection,
    Favorite,
    Product,
    Review,
    Room,
    Style,
)
from .serializers import (
    AdminProductSerializer,
    BannerSerializer,
    CategorySerializer,
    CollectionSerializer,
    FAQSerializer,
    FavoriteSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ReviewSerializer,
    RoomSerializer,
    StyleSerializer,
)


class CategoryList(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(is_active=True).annotate(
            products_count=Count("products", filter=Q(products__is_active=True))
        )


def _product_queryset():
    return (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants__color", "styles", "rooms")
        .annotate(
            reviews_count=Count(
                "reviews", filter=Q(reviews__is_published=True), distinct=True
            )
        )
    )


class ProductList(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name_uz", "name_ru", "material"]
    ordering_fields = ["base_price", "created_at", "rating_avg", "views_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return _product_queryset().distinct()


class ProductDetail(generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return _product_queryset()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Throttle view-count bumps per session to resist bot inflation.
        seen_key = f"seen_product_{instance.pk}"
        if not request.session.get(seen_key):
            Product.objects.filter(pk=instance.pk).update(views_count=F("views_count") + 1)
            request.session[seen_key] = True
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ProductReviewList(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_product(self):
        return generics.get_object_or_404(Product, slug=self.kwargs["slug"])

    def get_queryset(self):
        return Review.objects.filter(
            product__slug=self.kwargs["slug"], is_published=True
        ).select_related("user")

    def perform_create(self, serializer):
        product = self.get_product()
        user = self.request.user
        # Only buyers may review the product they purchased.
        order_item = (
            OrderItem.objects.filter(order__user=user, variant__product=product)
            .select_related("order")
            .first()
        )
        if not order_item:
            raise ValidationError("Sharh faqat mahsulotni sotib olganlar uchun.")
        if Review.objects.filter(product=product, user=user).exists():
            raise ValidationError("Siz bu mahsulotga allaqachon sharh qoldirgansiz.")
        serializer.save(user=user, product=product, order=order_item.order, is_published=False)


class CollectionList(generics.ListAPIView):
    serializer_class = CollectionSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Collection.objects.filter(is_active=True).prefetch_related(
            "products__images", "products__variants__color"
        )


class StyleList(generics.ListAPIView):
    serializer_class = StyleSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Style.objects.filter(is_active=True)


class RoomList(generics.ListAPIView):
    serializer_class = RoomSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Room.objects.filter(is_active=True)


class BannerList(generics.ListAPIView):
    serializer_class = BannerSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Banner.objects.filter(is_active=True)


class FAQList(generics.ListAPIView):
    serializer_class = FAQSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = FAQ.objects.filter(is_active=True)


class FavoriteList(generics.ListCreateAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related(
            "product__category"
        ).prefetch_related("product__images", "product__variants__color")

    def create(self, request, *args, **kwargs):
        product_id = request.data.get("product_id")
        if not product_id:
            raise ValidationError({"product_id": "Majburiy maydon."})
        product = generics.get_object_or_404(Product, pk=product_id, is_active=True)
        fav, created = Favorite.objects.get_or_create(user=request.user, product=product)
        serializer = self.get_serializer(fav)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FavoriteDelete(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = "product_id"

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def get_object(self):
        return generics.get_object_or_404(
            self.get_queryset(), product_id=self.kwargs["product_id"]
        )


class AdminProductList(generics.ListCreateAPIView):
    serializer_class = AdminProductSerializer
    permission_classes = [IsStaffRole]
    queryset = Product.objects.all()
    filterset_fields = ["category", "is_active", "is_new"]
    search_fields = ["slug", "name_uz", "name_ru"]


class AdminProductDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AdminProductSerializer
    permission_classes = [IsStaffRole]
    queryset = Product.objects.all()
    lookup_field = "slug"
