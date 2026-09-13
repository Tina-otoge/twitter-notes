import pydantic
from pydantic import BaseModel, ConfigDict


def valid_user_id(value):
    return (
        isinstance(value, str)
        and value.isascii()
        and value.isdigit()
        and 0 < len(value) <= 20
    )


class NoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = pydantic.Field(min_length=1, max_length=15)
    body: str = pydantic.Field(default="", max_length=10000)
    tag_ids: list[int] = pydantic.Field(default_factory=list, max_length=100)

    @pydantic.field_validator("username")
    @classmethod
    def check_username(cls, value):
        if not value.isascii() or not value.replace("_", "").isalnum():
            raise ValueError("Invalid Twitter handle")
        return value


class TagInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = pydantic.Field(min_length=1, max_length=50)
    color: str = "#198754"

    @pydantic.field_validator("color")
    @classmethod
    def check_color(cls, value):
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("Use a six-digit hex color")
        if any(
            character not in "0123456789abcdefABCDEF" for character in value[1:]
        ):
            raise ValueError("Invalid hex color")
        return value
