import pytest
from src.shared import base_types
from decimal import Decimal
from src.company.domain import aggregate, events


##### COMPANY TEST ######################


@pytest.mark.unittest
def test_should_create_new_company() -> None:
    company = aggregate.Company.create(
        name="TEST", address="test address", country=base_types.Country.USA
    )
    assert issubclass(aggregate.Company, base_types.DomainAggregate)
    assert isinstance(company.events[0], events.CompanyCreated)
    assert company.is_enabled()
