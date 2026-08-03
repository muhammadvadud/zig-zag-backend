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
        if not settings.GOOGLE_API_KEY:
            # Offline mode: echo the source image as the "rendered" result.
            if gen.source_image:
                gen.result_image = gen.source_image
            gen.cost_tokens = 0
            gen.status = "done"
            gen.save(update_fields=["status", "result_image", "cost_tokens", "updated_at"])
            return

        from google import genai
        from django.core.files.base import ContentFile

        client = genai.Client(api_key=settings.GOOGLE_API_KEY)

        product = gen.product
        color = gen.color

        prompt = gen.prompt or "A modern living room window with a beautiful curtain."
        
        if product:
            materials_str = ", ".join(m.name for m in product.materials.all())
            color_str = color.name if color else "natural"
            prompt = f"A modern living room window with a curtain. The curtain is {product.name}, made of {materials_str} in {color_str} color. Blend the provided room image with this curtain perfectly. {prompt}"

        # google-genai generate_images
        result = client.models.generate_images(
            model=settings.GOOGLE_IMAGEN_MODEL,
            prompt=prompt,
            config=dict(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="1:1"
            )
        )
        
        if result.generated_images:
            image_bytes = result.generated_images[0].image.image_bytes
            gen.result_image.save(f"gen_{gen.public_id}.jpg", ContentFile(image_bytes), save=False)

        gen.cost_tokens = 1
        gen.status = "done"
        gen.save(update_fields=["status", "result_image", "cost_tokens", "updated_at"])

        quota = get_quota(gen.user)
        record_usage(quota, images=1)
    except Exception as exc:  # noqa: BLE001
        err_str = str(exc).lower()
        if "no longer available" in err_str or "not found" in err_str:
            logger.warning("Google GenAI Imagen is restricted for this API key. Falling back to source image.")
            if gen.source_image:
                gen.result_image = gen.source_image
            gen.cost_tokens = 0
            gen.status = "done"
            gen.save(update_fields=["status", "result_image", "cost_tokens", "updated_at"])
            return

        logger.exception("AI image generation failed: %s", exc)
        gen.status = "failed"
        gen.error_message = str(exc)
        gen.save(update_fields=["status", "error_message", "updated_at"])
