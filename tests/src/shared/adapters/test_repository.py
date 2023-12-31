import pytest
import mock
from typing import Any, Dict, Iterator
from unittest.mock import MagicMock
from src.shared.adapters.persistence.dynamodb_repository import DynamoDbRepository
from src.shared.adapters import unit_of_work
from src.shared import base_types


class MockEntityId(base_types.EntityId):
    value: str


class MockEntity(base_types.RootEntity):
    id: MockEntityId


@pytest.fixture(scope="function")
def item_mock() -> MockEntity:
    return MockEntity(id=MockEntityId(value="123"))


@pytest.fixture(scope="function")
def dynamodb_repository_instance(uow: unit_of_work.UnitOfWork) -> DynamoDbRepository:
    repo = DynamoDbRepository(
        session=uow.session, table_name="test_table", entity_type=MockEntity
    )
    return repo


@pytest.mark.unittest
def test_dynamodb_put(
    uow: unit_of_work.UnitOfWork,
    dynamodb_repository_instance: DynamoDbRepository,
    item_mock: MockEntity,
):
    with uow.transaction():
        dynamodb_repository_instance.put(item_mock)
    record_registred = dynamodb_repository_instance.find_by_id(id=item_mock.id)
    assert record_registred


@pytest.mark.unittest
def test_should_dynamodb_find_by_id_return_item(
    dynamodb_repository_instance: DynamoDbRepository,
    item_mock: MockEntity,
) -> None:
    dynamodb_repository_instance.get_by_id = mock.MagicMock(return_value=item_mock)
    result = dynamodb_repository_instance.find_by_id(item_mock.id)
    dynamodb_repository_instance.get_by_id.assert_called_once_with(id=item_mock.id)
    assert result == item_mock


@pytest.mark.unittest
def test_should_dynamodb_find_by_id_return_None_if_item_not_exist(
    dynamodb_repository_instance: DynamoDbRepository, item_mock: MockEntity
) -> None:
    dynamodb_repository_instance.get_by_id = mock.MagicMock(
        side_effect=ValueError("Error")
    )
    result = dynamodb_repository_instance.find_by_id(item_mock.id)
    dynamodb_repository_instance.get_by_id.assert_called_once_with(id=item_mock.id)
    assert result == None


@pytest.mark.unittest
def test_should_dynamodb_get_all_successfuly(
    dynamodb_repository_instance: DynamoDbRepository, item_mock: MockEntity
) -> None:
    dynamodb_repository_instance.get_by_id = mock.MagicMock(return_value=item_mock)
    result = dynamodb_repository_instance.find_by_id(item_mock.id)
    dynamodb_repository_instance.get_by_id.assert_called_once_with(id=item_mock.id)
    assert result == item_mock
