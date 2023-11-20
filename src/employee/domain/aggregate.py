import enum
from typing import List
from pydantic import EmailStr
from src.shared import base_types
from src.shared.base_types import update_last_udpate_date
from src.employee.domain import events


######### Employee ##################################


class EmployeeId(base_types.EntityId):
    name: str
    email: EmailStr


class EmployeeStatus(base_types.NamedEnum):
    ACTIVE = enum.auto()
    INACTIVE = enum.auto()
    BLOCKED = enum.auto()


class Employee(base_types.DomainAggregate):
    id: EmployeeId
    company_id: str
    status: EmployeeStatus
    _events: List[base_types.DomainEvent] = []

    @classmethod
    def create(cls, name: str, email: str, company_id: str) -> "Employee":
        entity = cls(
            id=EmployeeId(name=name, email=EmailStr(email)),
            company_id=company_id,
            status=EmployeeStatus.ACTIVE,
        )
        entity.add_event(
            events.EmployeeCreated(
                employee_id=entity.id._key(),
                name=name,
                company_id=company_id,
            )
        )
        return entity

    @update_last_udpate_date
    def active(self):
        self.status = EmployeeStatus.ACTIVE
        self._events.append(events.EmployeeActivated(employee_id=self.id.email))

    @update_last_udpate_date
    def inactive(self):
        self.status = EmployeeStatus.INACTIVE
        self._events.append(events.EmployeeDisabled(employee_id=self.id.email))

    @update_last_udpate_date
    def block(self):
        self.status = EmployeeStatus.BLOCKED
        self._events.append(events.EmployeeBlocked(employee_id=self.id.email))

    def is_actived(self):
        return self.status == EmployeeStatus.ACTIVE

    def is_inactived(self):
        return self.status == EmployeeStatus.INACTIVE

    def is_blocked(self):
        return self.status == EmployeeStatus.BLOCKED
