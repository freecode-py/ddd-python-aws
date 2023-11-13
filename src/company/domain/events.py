import pydantic
from typing import Literal
from src.shared import base_types


class _CompanyEvent(base_types.DomainEvent):
    domain_name: str = pydantic.Field(default="Company")


class CompanyCreated(_CompanyEvent):
    company_id: str
    name: str
    address: str
    country: base_types.Country
