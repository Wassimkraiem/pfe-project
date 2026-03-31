import json


def extract_clerk_error_message(error: Exception) -> str:
    """Extract the first Clerk validation message from an exception payload."""
    raw_error = str(error)

    errors_attr = getattr(error, "errors", None)
    if isinstance(errors_attr, list) and errors_attr:
        first_error = errors_attr[0]
        if isinstance(first_error, dict):
            message = first_error.get("message")
            if isinstance(message, str) and message.strip():
                return message

    try:
        payload = json.loads(raw_error)
    except json.JSONDecodeError:
        return raw_error

    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            first_error = errors[0]
            if isinstance(first_error, dict):
                message = first_error.get("message")
                if isinstance(message, str) and message.strip():
                    return message

    return raw_error
