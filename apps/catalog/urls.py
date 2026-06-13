from django.urls import path

from .views import (
    AdminProductDetail,
    AdminProductList,
    BannerList,
    CategoryList,
    CollectionList,
    FAQList,
    FavoriteDelete,
    FavoriteList,
    ProductDetail,
    ProductList,
    ProductReviewList,
)

urlpatterns = [
    path("categories/", CategoryList.as_view(), name="category-list"),
    path("products/", ProductList.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetail.as_view(), name="product-detail"),
    path("products/<slug:slug>/reviews/", ProductReviewList.as_view(), name="product-reviews"),
    path("collections/", CollectionList.as_view(), name="collection-list"),
    path("banners/", BannerList.as_view(), name="banner-list"),
    path("faq/", FAQList.as_view(), name="faq-list"),
    path("favorites/", FavoriteList.as_view(), name="favorite-list"),
    path("favorites/<int:product_id>/", FavoriteDelete.as_view(), name="favorite-delete"),
    # Admin
    path("admin/products/", AdminProductList.as_view(), name="admin-product-list"),
    path("admin/products/<slug:slug>/", AdminProductDetail.as_view(), name="admin-product-detail"),
]
