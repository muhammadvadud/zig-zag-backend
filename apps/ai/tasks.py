import logging

from celery import shared_task
from django.conf import settings

from .models import AIImageGeneration
from .quota import get_quota, record_usage

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_ai_image(self, generation_id):
    """Run an image generation job off the request thread (Celery)."""

    try:
        gen = AIImageGeneration.objects.get(pk=generation_id)
    except AIImageGeneration.DoesNotExist:
        return

    gen.status = "processing"
    gen.save(update_fields=["status", "updated_at"])

    try:
        if settings.AI_STUB_MODE or not settings.ANTHROPIC_API_KEY:
            # Offline mode: echo the source image as the "rendered" result.
            if gen.source_image:
                gen.result_image = gen.source_image
            gen.cost_tokens = 0
        else:
            # Real image-model integration goes here (room + curtain compose).
            raise NotImplementedError("Image model integration not configured.")

        gen.status = "done"
        gen.save(update_fields=["status", "result_image", "cost_tokens", "updated_at"])

        quota = get_quota(gen.user)
        record_usage(quota, images=1)
    except Exception as exc:  # noqa: BLE001
        logger.exception("AI image generation failed: %s", exc)
        gen.status = "failed"
        gen.error_message = str(exc)
        gen.save(update_fields=["status", "error_message", "updated_at"])
