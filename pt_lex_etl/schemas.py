import re
import datetime
from pydantic import BaseModel, field_validator, ValidationError


class DiplomaMetadata(BaseModel):
    code: str
    version: str | None = None

    @field_validator("code")
    def validate_diploma_code(cls, value):
        try:
            code_elements = re.split(r" +", value)
            assert bool(
                re.match(r"(decreto-lei|lei|portaria)", code_elements[0].lower())
            ), f"'{code_elements[0]}' does NOT match any of the diploma types."

            code_ending = code_elements[-1].split("/")
            assert (
                len(code_ending) <= 2
            ), f"The diploma's code number or year is not correctly defined."

            if len(code_ending) == 2:
                current_year = datetime.datetime.now().year + 1
                assert (
                    int(code_ending[-1]) <= current_year
                ), f"Diploma's year cannot be greater than {current_year}"

            assert bool(
                re.match(r"^([0-9]+)(\-[a-zA-Z])?$", code_ending[0])
            ), f"The diploma's code number is not correctly defined."

            return f"{code_elements[0]} n.º {code_elements[-1]}"

        except Exception as e:
            raise e

    @field_validator("version")
    def version_is_datelike(cls, value):
        if value is None:
            return value

        date_format = "%Y-%m-%d"
        assert datetime.datetime.strptime(value, date_format)
        return value
