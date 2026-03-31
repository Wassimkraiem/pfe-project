from http import HTTPStatus


class MissingEnvironmentVariableException(Exception):
    pass

class ItemNotFoundException(Exception):
    status_code = HTTPStatus.NOT_FOUND
    message = "item not found"
    