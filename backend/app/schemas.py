from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Strict):
    login_id: str = Field(min_length=1, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=1, max_length=128)


class PasswordChange(Strict):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class Profile(Strict):
    expected_version: int = Field(default=0, ge=0)
    display_name: str = Field(default="", max_length=40)
    language: Literal["zh", "en", "ja"] = "zh"
    age: int | None = Field(default=None, ge=1, le=120)
    height_cm: float | None = Field(default=None, ge=70, le=240, allow_inf_nan=False)
    weight_kg: float | None = Field(default=None, ge=20, le=250, allow_inf_nan=False)
    activity: Literal["low", "moderate", "high"] = "moderate"
    income_band: (
        Literal["JPY_A1", "JPY_A2", "JPY_A3", "JPY_A4", "JPY_A5", "JPY_A6"] | None
    ) = None
    daily_budget: int | None = Field(default=None, ge=100, le=20000)
    allergy_status: Literal["unknown", "none", "present"] = "unknown"
    allergens: list[Literal["milk", "egg", "soy", "wheat", "fish", "nuts", "other"]] = (
        Field(default_factory=list, max_length=7)
    )
    conditions: list[
        Literal["hypertension", "diabetes", "kidney", "pregnancy", "other"]
    ] = Field(default_factory=list, max_length=5)
    health_confirmed: bool = False
    diet: Literal["any", "vegetarian"] = "any"
    dislikes: list[str] = Field(default_factory=list, max_length=30)
    cooking_minutes: int = Field(default=45, ge=10, le=120)
    region: Literal["Japan-demo"] = "Japan-demo"
    demo_consent: bool = False
    energy_kcal: int = Field(default=2000, ge=1200, le=3200)
    sodium_max_mg: int = Field(default=2000, ge=500, le=3000)

    @field_validator("dislikes")
    @classmethod
    def food_codes(cls, vs):
        if any(len(v) != 5 or not v.isdigit() for v in vs):
            raise ValueError("Use food IDs")
        return sorted(set(vs))


class BP(Strict):
    systolic: int = Field(ge=50, le=300)
    diastolic: int = Field(ge=30, le=200)
    measured_at: datetime


class PlanRequest(Strict):
    language: Literal["zh", "en", "ja"] | None = None
    budget: int | None = Field(default=None, ge=100, le=20000)
    budget_min: int | None = Field(default=None, ge=100, le=20000)
    idempotency_key: str = Field(
        min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"
    )

    @model_validator(mode="after")
    def budget_interval(self):
        if self.budget_min is not None and (self.budget is None or self.budget_min > self.budget):
            raise ValueError("A budget minimum requires a maximum at least as high")
        return self


class SubstituteRequest(PlanRequest):
    meal: Literal["breakfast", "lunch", "dinner"]


class ChatRequest(Strict):
    language: Literal["zh", "en", "ja"] | None = None
    message: str = Field(min_length=1, max_length=1500)
    session_id: str | None = Field(default=None, max_length=40)
    idempotency_key: str = Field(
        min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"
    )
