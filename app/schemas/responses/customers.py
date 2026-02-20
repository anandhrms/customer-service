from pydantic import BaseModel


class CustomerData(BaseModel):
    customer_id: int
    pic_url: str
    analyst_blacklisted: bool | None = None
    app_blacklisted: bool | None = None
    created_at: str


class GetCustomersResponse(BaseModel):
    interval: str | None = None
    label: str | None = None
    data: list[CustomerData]
