import contextlib
import os
import json
from decimal import Decimal
from typing import Any
from typing import Optional
from datetime import datetime
from dateutil.parser import parse as parse_date
from marshmallow import fields, ValidationError
from sev.exceptions import MissingEnvironmentVariableException


def get_env(name: str, default: Optional[str] = None, required: bool = False) -> Any:
    """
    Gets an environment variable and converts it to its true type.

    Args:
        name (str): Name of the environment variable.
        default (Optional[str]): Default value if the environment variable is not set.
        required (bool): Flag to enforce the presence of the environment variable.

    Returns:
        Any: The environment variable.

    Raises:
        ImproperlyConfigured: If the environment variable is not set and required is True.
    """
    try:
        value = os.environ[name]
    except KeyError as e:
        if required:
            raise MissingEnvironmentVariableException(
                f"Missing environment variable: {name}"
            ) from e
        value = default
    return convert_to_true_type(value) or default


def convert_to_true_type(value: Optional[str]) -> Any:
    """
    Converts a string to its true type.

    Args:
        value (Optional[str]): String to convert.

    Returns:
        Any: The converted value.
    """
    if value is None:
        return None
    if value.title() == "True":
        return True
    if value.title() == "False":
        return False
    if value.title() == "None":
        return None
    with contextlib.suppress(ValueError):
        return int(value)
    with contextlib.suppress(ValueError):
        return float(value)
    return value


class DateToStringField(fields.Field):
    """
    Custom field for serializing and deserializing dates as strings.
    """

    def _deserialize(self, value, attr, data, **kwargs) -> str:
        if not value:
            raise ValidationError("Field may not be null.")
        try:
            date = parse_date(value)
        except (ValueError, TypeError) as e:
            raise ValidationError("Invalid date format.") from e

        return date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _serialize(self, value, attr, obj, **kwargs) -> str:
        if not isinstance(value, str):
            raise ValidationError("Invalid type for date value. Expected string.")
        return value


def convert_floats_to_decimals(data):
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = convert_floats_to_decimals(value)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            data[index] = convert_floats_to_decimals(data[value])
    elif isinstance(data, float):
        return Decimal(str(data))
    return data


def convert_decimals(obj):
    if isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, Decimal):
        return float(obj)  # Convert Decimal to float
    return obj
