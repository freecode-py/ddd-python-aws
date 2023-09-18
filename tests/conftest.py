import os

import pytest
from src.shared.adapters import unit_of_work


def pytest_generate_tests(metafunc):
    os.environ["AWS_REGION"] = "us-east-2"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-2"
    os.environ["AWS_ACCESS_KEY_ID"] = "1111111"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "111111"


@pytest.fixture
def uow() -> unit_of_work.UnitOfWork:
    return unit_of_work.FakeUnitOfWork()
