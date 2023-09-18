import pydantic
from src.shared import base_types


class CompanyCreated(base_types.DomainEvent):
    company_id: str
    address: str
    country: base_types.Country
