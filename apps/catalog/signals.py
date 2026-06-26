from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review
from .ratings import recompute_product_rating


@receiver(post_save, sender=Review)
def review_saved(sender, instance, **kwargs):
    recompute_product_rating(instance.product)


@receiver(post_delete, sender=Review)
def review_deleted(sender, instance, **kwargs):
    recompute_product_rating(instance.product)
