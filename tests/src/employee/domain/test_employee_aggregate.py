import pytest
from src.shared import base_types
from decimal import Decimal
from src.employee.domain import aggregate, events

##### Employee TEST ######################


@pytest.mark.unittest
def test_should_create_Employee_successfuly() -> None:
    employee = aggregate.Employee.create(
        name="Employee test",
        email="employee_test@gmail.com",
        company_id="test_company",
    )
    assert employee
    assert employee.is_actived()
    assert len(employee.events) == 1
    event = employee.events[0]
    assert isinstance(event, events.EmployeeCreated)
