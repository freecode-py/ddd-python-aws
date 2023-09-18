import enum
from typing import List
from pydantic import EmailStr
from src.shared import base_types
from src.shared.base_types import update_last_udpate_date
from src.company.domain import events


######### Company ##################################


class CompanyId(base_types.EntityId):
    value: str


class CompanyStatus(base_types.NamedEnum):
    ENABLED = enum.auto()
    DISABLED = enum.auto()


class Company(base_types.DomainAggregate):
    id: CompanyId
    name: str
    address: str
    status: CompanyStatus
    country: base_types.Country
    _events: List[base_types.DomainEvent] = []

    @classmethod
    def create(
        cls, *, name: str, address: str, country: base_types.Country
    ) -> "Company":
        entity = cls(
            id=CompanyId(value=name),
            name=name,
            address=address,
            status=CompanyStatus.ENABLED,
            country=country,
        )
        entity.add_event(
            event=events.CompanyCreated(
                company_id=entity.id.value,
                name=name,
                address=address,
                country=country,
            )
        )
        return entity

    @update_last_udpate_date
    def enable(self):
        self.status = CompanyStatus.ENABLED

    @update_last_udpate_date
    def disable(self):
        self.status = CompanyStatus.DISABLED

    def is_enabled(self):
        return self.status == CompanyStatus.ENABLED

    def is_disabled(self):
        return self.status == CompanyStatus.DISABLED
