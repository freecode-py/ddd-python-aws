import enum
import contextlib
import abc
import boto3
import backoff
from botocore import exceptions as boto3_exceptions
from typing import Protocol, TypeVar, List, Iterator, Dict, Any, Type
from src.shared import logging
from src.shared import base_types
from src.shared.adapters import event_publisher

_LOGGER = logging.Logger("Unit of Work")

E = TypeVar("E", bound=base_types.RepositoryAggregate)
I = TypeVar("I", bound=base_types.EntityId)
DE = TypeVar("DE", bound=base_types.DomainEvent)


class UnknownTransactionTypeError(Exception):
    ...


class TransactionType(base_types.NamedEnum):
    SINGLE = enum.auto()
    BATCH = enum.auto()
    NONE = enum.auto()


class UnitOfWork(Protocol):
    def transaction(self) -> None:
        ...

    def batch(self) -> None:
        ...

    def commit(self) -> None:
        ...

    def get_item_by_id(
        self, table_name: str, key_name: str, id: I, entity_type: Type[E]
    ) -> E:
        ...

    def get_all_items(self, table_name: str, entity_type: Type[E]) -> Iterator[E]:
        ...

    def add_put_operation(self, table_name: str, key_name: str, item: E) -> None:
        ...

    def add_update_operation(self, table_name: str, key_name: str, item: E) -> None:
        ...

    def rollback(self) -> None:
        ...

    def publish_events(self, events: List[DE]) -> None:
        ...


MAX_DYNAMO_DB_BATCH_SIZE_PER_TRX = 100


class DynamoDbUnitOfWork:
    def __init__(
        self,
    ) -> None:
        self._dynamodb_client = boto3.client("dynamodb")
        self._message_bus_client = event_publisher.EventBridgePublisher()
        self._batches = _DynamoDbWriteOperationsBuilder(
            dynamodb_client=self._dynamodb_client
        )
        self._events_to_publish: List[DE] = []
        self._transaction_type: TransactionType = TransactionType.NONE

    @contextlib.contextmanager
    def transaction(self) -> None:
        try:
            _LOGGER.info("Init in single transaction context manager")
            self._transaction_type = TransactionType.SINGLE
            yield
            self.commit()
        finally:
            self._transaction_type = TransactionType.NONE
            self._events_to_publish.clear()

    @contextlib.contextmanager
    def batch(self) -> None:
        try:
            _LOGGER.info("Init in batch transaction context manager")
            self._transaction_type = TransactionType.BATCH
            yield
            self.commit()
        finally:
            self._transaction_type = TransactionType.NONE
            self._events_to_publish.clear()

    def commit(self) -> None:
        if self._transaction_type == TransactionType.SINGLE:
            self._batches.execute_in_single_transaction()
        elif self._transaction_type == TransactionType.BATCH:
            self._batches.execute_in_batch_transaction()
        else:
            raise UnknownTransactionTypeError(
                "Error when try to identify the transaction type. For now we only allow SINGLE and BATCH transaction types"
            )
        if self._events_to_publish:
            _LOGGER.info("Publishing event domain associated")
            self._message_bus_client.publish(events=self._events_to_publish)

    @classmethod
    def _deserializer_item(cls, dynamodb_record: Dict[str, Any]) -> Dict[str, Any]:
        from boto3.dynamodb.types import TypeDeserializer

        deserializer = TypeDeserializer()
        parsed_record = {
            k: deserializer.deserialize(v) for k, v in dynamodb_record.items()
        }
        return parsed_record

    @classmethod
    def serialize_entity(cls, entity: E) -> Dict[str, Any]:
        from decimal import Decimal

        nested_dict = entity.dict()
        for k, v in nested_dict.items():
            if isinstance(v, Decimal):
                nested_dict[k] = float(v)
        return nested_dict

    def get_item_by_id(
        self, table_name: str, key_name: str, id: I, entity_type: Type[E]
    ) -> E:
        item = self._dynamodb_client.get_item(
            TableName=table_name, Key={key_name: {"S": id._key()}}
        ).get("Item")
        if item:
            print(f"Aggregate type: {entity_type}")
            item_deserialized = self._deserializer_item(dynamodb_record=item)
            print(f"Item result: {item_deserialized}")
            return entity_type.parse_obj(item_deserialized)
        raise ValueError(f"Item with id {id._key()} not found")

    def get_all_items(self, table_name: str, entity_type: type[E]) -> Iterator[E]:
        params = {"TableName": table_name, "Limit": MAX_DYNAMO_DB_BATCH_SIZE_PER_TRX}
        while True:
            response = self._dynamodb_client.scan(**params)
            items = response.get("Items", [])
            for item in items:
                yield entity_type.parse_obj(item)

            if "LastEvaluatedKey" in response:
                params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            else:
                break

    def add_put_operation(self, table_name: str, key_name: str, item: E) -> None:
        self._add_operation(
            table_name=table_name,
            key_name=key_name,
            item=item,
            operation_type=_DynamoDbPutOperation,
        )

    def add_update_operation(self, table_name: str, key_name: str, item: E) -> None:
        self._add_operation(
            table_name=table_name,
            key_name=key_name,
            item=item,
            operation_type=_DynamoDbUpdateOperation,
        )

    def _add_operation(
        self,
        table_name: str,
        key_name: str,
        item: E,
        operation_type: Type["_DynamoDbWriteOperation"],
    ) -> None:
        # In case of error we don't update the real item in memory
        item_to_save = item.copy()
        item_to_save._increase_version()
        record_serialized = self.serialize_entity(item_to_save)
        record_serialized[key_name] = item_to_save.id._key()
        operation = operation_type(
            table_name=table_name, key_name=key_name, entity_dict=record_serialized
        )
        self._batches.add_operation(operation)

    def rollback(self) -> None:
        ...

    def publish_events(self, events: List[DE]) -> None:
        self._events_to_publish.extend(events)


class FakeUnitOfWork:
    def __init__(
        self,
    ) -> None:
        self._commited = False
        self._transaction_type: TransactionType = TransactionType.NONE
        self._batches: Dict[str, E] = {}

    @contextlib.contextmanager
    def transaction(self) -> None:
        try:
            _LOGGER.info("Init in single transaction context manager")
            self._transaction_type = TransactionType.SINGLE
            yield
            self.commit()
        finally:
            self._transaction_type = TransactionType.NONE

    @contextlib.contextmanager
    def batch(self) -> None:
        try:
            _LOGGER.info("Init in batch transaction context manager")
            self._transaction_type = TransactionType.BATCH
            yield
            self.commit()
        finally:
            self._transaction_type = TransactionType.NONE

    def commit(self) -> None:
        self._commited = True

    def get_item_by_id(
        self, table_name: str, key_name: str, id: I, entity_type: type[E]
    ) -> E:
        return self._batches[id._key()]

    def get_all_items(self, table_name: str, entity_type: type[E]) -> Iterator[E]:
        return iter([*self._batches.values()])

    def add_put_operation(self, table_name: str, key_name: str, item: E):
        self._batches[item.id._key()] = item

    def add_update_operation(self, table_name: str, key_name: str, item: E) -> None:
        self._batches[item.id._key()] = item

    def rollback(self) -> None:
        ...


class _WriteOperation(abc.ABC):
    @property
    def id(self) -> str:
        ...

    @property
    def key_name(self) -> str:
        ...

    @property
    def table_name(self) -> str:
        ...

    @property
    def entity_serialized(self) -> Dict[str, Any]:
        ...


############## DYNAMO DB WRITE OPERATION IN DB COMPONENTS ####################################################
class DuplicateWriteOperationsError(Exception):
    def __init__(self) -> None:
        super().__init__(
            message="A single write operation for each entity is allowed in the same context"
        )


class DynamoBatchSizePerTrxExceedsError(Exception):
    def __init__(self) -> None:
        super().__init__(
            message="DynamoDB only allows 100 operations in a single transaction"
        )


class WrongProcessTransactionTypeSelectedError(Exception):
    ...


class TransactionFailedError(Exception):
    ...


class _DynamoDbWriteOperation(_WriteOperation):
    def __init__(
        self, table_name: str, key_name: str, entity_dict: Dict[str, Any]
    ) -> None:
        self._table_name = table_name
        self._key_name = key_name
        self._id = entity_dict.get(key_name)
        self._entity = entity_dict

    @property
    def id(self) -> str:
        return self._id

    @property
    def key_name(self) -> str:
        self._key_name

    @property
    def table_name(self) -> str:
        self._table_name

    @property
    def entity_serialized(self) -> Dict[str, Any]:
        from boto3.dynamodb.types import TypeSerializer

        serializer = TypeSerializer()
        dynamodb_dict = {k: serializer.serialize(v) for k, v in self._entity.items()}
        return dynamodb_dict


class _DynamoDbPutOperation(_DynamoDbWriteOperation):
    def __init__(
        self, table_name: str, key_name: str, entity_dict: Dict[str, Any]
    ) -> None:
        super().__init__(table_name, key_name, entity_dict)

    @property
    def id(self) -> str:
        return super().id

    @property
    def table_name(self) -> str:
        return super().table_name

    @property
    def key_name(self) -> str:
        return super().key_name

    @property
    def entity_serialized(self) -> Dict[str, Any]:
        entity_dict = super().entity_serialized
        return {
            "Put": {
                "Item": entity_dict,
                "TableName": self._table_name,
                "ConditionExpression": "attribute_not_exists(#id)",
                "ExpressionAttributeNames": {"#id": self._key_name},
                "ReturnValuesOnConditionCheckFailure": "ALL_OLD",
            }
        }


class _DynamoDbUpdateOperation(_DynamoDbWriteOperation):
    def __init__(
        self, table_name: str, key_name: str, entity_dict: Dict[str, Any]
    ) -> None:
        super().__init__(table_name, key_name, entity_dict)

    @property
    def id(self) -> str:
        return super().id

    @property
    def table_name(self) -> str:
        return super().table_name

    @property
    def key_name(self) -> str:
        return super().key_name

    @property
    def entity_serialized(self) -> Dict[str, Any]:
        entity_dict = super().entity_serialized
        key_value = entity_dict.pop(self.key_name)
        update_expression_parts = []
        for attr_name in entity_dict:
            update_expression_parts.append(f"#{attr_name} = :{attr_name}")
        update_expression = "SET " + ", ".join(update_expression_parts)
        return {
            "Update": {
                "TableName": self.table_name,
                "Key": key_value,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": entity_dict,
            }
        }


class _WriteOperationBuilder(abc.ABC):
    def clear(self) -> None:
        ...

    def add_operation(self, operation: _WriteOperation) -> None:
        ...

    def execute_in_single_transaction(self) -> None:
        ...

    def execute_in_batch_transaction(self) -> None:
        ...


class _DynamoDbWriteOperationsBuilder(_WriteOperationBuilder):
    def __init__(self, dynamodb_client: Any) -> None:
        self._dynamodb_client = dynamodb_client
        self._operations: Dict[str, Dict[str, Any]] = {}

    def clear(self) -> None:
        self._operations = {}

    def add_operation(self, operation: _WriteOperation) -> None:
        if self._operations.get(operation.id, None):
            raise DuplicateWriteOperationsError()
        self._operations[operation.id] = operation.entity_serialized

    @backoff.on_exception(backoff.fibo, TransactionFailedError, max_tries=3, max_time=4)
    def _write_items(self, items: List[Dict[str, Any]]):
        try:
            self._dynamodb_client.transact_write_items(TransactItems=items)
        except boto3_exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            _LOGGER.exception(f"Transaction error {error_code}. Exception {str(e)}")
            if error_code == "TransactionCanceledException":
                raise TransactionFailedError(
                    ".".join(
                        reason["Message"]
                        for reason in e.response["CancellationReasons"]
                    )
                )
            raise TransactionFailedError(error_code) from e
        except Exception as e:
            _LOGGER.exception(f"Transaction error. Exception {str(e)}")
            raise TransactionFailedError() from e

    def execute_in_single_transaction(self):
        if not self._operations:
            return
        if len(self._operations) > MAX_DYNAMO_DB_BATCH_SIZE_PER_TRX:
            raise DynamoBatchSizePerTrxExceedsError()
        self._write_items(items=list(self._operations.values()))
        self.clear()

    def execute_in_batch_transaction(self):
        if not self._operations:
            return
        operations_spplitted: Iterator[List[Dict[str, Any]]] = base_types.split_list(
            input_list=list(self._operations.values()),
            chunk_size=MAX_DYNAMO_DB_BATCH_SIZE_PER_TRX,
        )
        for operations in operations_spplitted:
            self._write_items(items=operations)
        self.clear()
