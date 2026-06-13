from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class BusinessError(APIException):
    """Raised for business-rule violations (HTTP 422)."""

    status_code = 422
    default_code = "business_error"
    default_detail = "Biznes-mantiq xatosi."


class Conflict(APIException):
    status_code = 409
    default_code = "conflict"
    default_detail = "Konflikt."


# Map DRF default codes to a stable machine-readable code.
_CODE_BY_STATUS = {
    400: "validation_error",
    401: "authentication_required",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "business_error",
    429: "throttled",
    500: "server_error",
}


def api_exception_handler(exc, context):
    """Wrap every error in the project's standard envelope."""

    response = exception_handler(exc, context)
    if response is None:
        return response

    status = response.status_code
    code = getattr(exc, "default_code", None) or _CODE_BY_STATUS.get(status, "error")

    data = response.data
    message = "So'rovni bajarib bo'lmadi."
    details = None

    if isinstance(data, dict):
        if "detail" in data and len(data) == 1:
            message = str(data["detail"])
        else:
            message = "Yuborilgan ma'lumotlar noto'g'ri."
            details = data
    elif isinstance(data, list):
        details = {"non_field_errors": data}

    response.data = {
        "error": {
            "code": code,
            "message": message,
            **({"details": details} if details else {}),
        }
    }
    return response
