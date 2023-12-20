import pytest
import mock
from src.shared.adapters import unit_of_work
from src.shared.adapters.persistence import commons as persistence_commons


@pytest.mark.unittest
def test_should_TransitionTypes_are_correct_values() -> None:
    assert unit_of_work.TransactionType.SINGLE == "SINGLE"
    assert unit_of_work.TransactionType.BATCH == "BATCH"
    assert unit_of_work.TransactionType.NONE == "NONE"


####### DynamoDB UnitOfWork #######################################
@pytest.fixture
def dynamodb_uow() -> unit_of_work.DynamoDbUnitOfWork:
    return unit_of_work.DynamoDbUnitOfWork()


@pytest.mark.unittest
def test_should_DynamoDb_uow_init_successfuly(
    dynamodb_uow: unit_of_work.DynamoDbUnitOfWork,
) -> None:
    assert dynamodb_uow._session
    assert isinstance(dynamodb_uow._session, unit_of_work.DefaultDynamoDBSession)
    assert dynamodb_uow._transaction_type == unit_of_work.TransactionType.NONE


@pytest.mark.unittest
def test_transaction_context_create_successfuly(
    dynamodb_uow: unit_of_work.DynamoDbUnitOfWork,
) -> None:
    with mock.patch.object(
        dynamodb_uow, "commit", return_value=None
    ) as commit_mock_method:
        with dynamodb_uow.transaction():
            assert dynamodb_uow._transaction_type == unit_of_work.TransactionType.SINGLE
    assert dynamodb_uow._transaction_type == unit_of_work.TransactionType.NONE
    commit_mock_method.assert_called_once


@pytest.mark.unittest
def test_should_batch_context_create_successfuly(
    dynamodb_uow: unit_of_work.DynamoDbUnitOfWork,
):
    with mock.patch.object(
        dynamodb_uow, "commit", return_value=None
    ) as commit_mock_method:
        with dynamodb_uow.batch():
            assert dynamodb_uow._transaction_type == unit_of_work.TransactionType.BATCH
    assert dynamodb_uow._transaction_type == unit_of_work.TransactionType.NONE
    commit_mock_method.assert_called_once


@pytest.mark.unittest
def test_should_commit_single_transaction_successfuly(
    dynamodb_uow: unit_of_work.DynamoDbUnitOfWork, mocker
) -> None:
    dynamodb_uow._transaction_type = unit_of_work.TransactionType.SINGLE
    mock_execute_single = mocker.patch.object(
        dynamodb_uow._session, "execute_in_single_transaction"
    )

    dynamodb_uow.commit()

    mock_execute_single.assert_called_once()


@pytest.mark.unittest
def test_should_commit_batch_transaction_successfuly(
    dynamodb_uow: unit_of_work.DynamoDbUnitOfWork, mocker
) -> None:
    dynamodb_uow._transaction_type = unit_of_work.TransactionType.BATCH
    mock_execute_batch = mocker.patch.object(
        dynamodb_uow._session, "execute_in_batch_transaction"
    )

    dynamodb_uow.commit()

    mock_execute_batch.assert_called_once()


# @pytest.mark.unittest
# def test_should_dynamodb_uow_deserializer_item_successfuly(
#     dynamodb_uow: unit_of_work.DynamoDbUnitOfWork,
# ) -> None:
#     item_db = {
#         "id._key": {"S": "SOLES SA"},
#         "address": {"S": "test_address"},
#         "country": {"S": "USA"},
#     }
#     item_deserialized = dynamodb_uow._deserializer_item(dynamodb_record=item_db)
#     assert isinstance(item_deserialized, dict)
#     assert item_deserialized == {
#         "id._key": "SOLES SA",
#         "address": "test_address",
#         "country": "USA",
#     }


# TODO: ADD MORE UNIT TESTS
