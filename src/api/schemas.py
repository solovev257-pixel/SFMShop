from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    quantity: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Название не может быть пустым")
        return value.strip()


class ProductUpdate(BaseModel):
    """Все поля необязательные: меняем только то, что прислали"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    price: float | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Название не может быть пустым")
        return value.strip() if value else value


class OrderItem(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[OrderItem] = Field(min_length=1, max_length=50)


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=100, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserLogin(BaseModel):
    email: str = Field(max_length=100, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SupportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1000)