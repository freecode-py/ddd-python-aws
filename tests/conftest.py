import os

import pytest
from src.shared.adapters import unit_of_work
from tests.src.fake_shared_adapters import FakeDynamoDbUnitOfWork


def pytest_generate_tests(metafunc):
    os.environ["AWS_REGION"] = "us-east-2"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-2"
    os.environ["AWS_ACCESS_KEY_ID"] = "1111111"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "111111"
    os.environ["EVENT_BRIDGE_TOPIC_ARN"] = "test-event-bridge-arn"
    os.environ["BACKOFF_DEFAULT_TRIES"] = "0"
    os.environ["BACKOFF_DEFAULT_MAX_TIME"] = "0"
    os.environ["AGGREGATE_COMPANY_TABLE_NAME"] = "company-aggregate-table"
    os.environ["AGGREGATE_COMPANY_TABLE_KEY_NAME"] = "id"


@pytest.fixture
def uow() -> unit_of_work.UnitOfWork:
    return FakeDynamoDbUnitOfWork()
