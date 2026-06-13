from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class CheckoutThrottle(UserRateThrottle):
    scope = "checkout"


class SearchThrottle(UserRateThrottle):
    scope = "search"


class AIChatThrottle(UserRateThrottle):
    scope = "ai_chat"


class AIChatDailyThrottle(UserRateThrottle):
    scope = "ai_chat_day"


class AIChatAnonThrottle(AnonRateThrottle):
    """Hard daily cap for anonymous AI demo usage."""

    scope = "ai_image"  # reuse the strict 10/day bucket for anon demo


class AIImageThrottle(UserRateThrottle):
    scope = "ai_image"
