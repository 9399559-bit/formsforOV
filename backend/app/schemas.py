import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class LeadCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    has_land: Optional[str] = None
    location: Optional[str] = None
    product_line: Optional[str] = None
    project: Optional[str] = None
    start_date: Optional[str] = None
    financing_source: Optional[str] = None
    budget: Optional[str] = None
    preferred_communication: Optional[str] = None
    comment: Optional[str] = None
    pdn_consent: bool

    @field_validator(
        "name",
        "phone",
        "has_land",
        "location",
        "product_line",
        "project",
        "start_date",
        "financing_source",
        "budget",
        "preferred_communication",
        "comment",
        mode="before",
    )
    @classmethod
    def strip_string_fields(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped.lower() or None
        return value

    @field_validator("phone", mode="after")
    @classmethod
    def normalize_phone(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None

        digits = re.sub(r"\D", "", value)
        if not digits:
            return None

        if len(digits) == 11 and digits.startswith("8"):
            digits = f"7{digits[1:]}"
        elif len(digits) == 10:
            digits = f"7{digits}"

        return f"+{digits}"

    @model_validator(mode="after")
    def validate_contacts_and_consent(self) -> "LeadCreateRequest":
        if not self.name:
            raise ValueError("Name is required.")

        if not self.phone and not self.email:
            raise ValueError("Either phone or email is required.")

        if not self.pdn_consent:
            raise ValueError("Personal data consent is required.")

        return self


class LeadCreateResponse(BaseModel):
    success: bool
    message: str
    lead_id: Optional[int] = None
