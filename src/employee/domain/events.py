import pydantic
from src.shared import base_types


class EmployeeCreated(base_types.DomainEvent):
    employee_id: str
    name: str
    company_id: str


class _EmployeeStatusUpdated(base_types.DomainEvent):
    employee_id: str
    last_update: base_types.EpochTime = pydantic.Field(
        default_factory=base_types.EpochTime.now
    )


class EmployeeActivated(_EmployeeStatusUpdated):
    ...


class EmployeeDisabled(_EmployeeStatusUpdated):
    ...


class EmployeeBlocked(_EmployeeStatusUpdated):
    ...
