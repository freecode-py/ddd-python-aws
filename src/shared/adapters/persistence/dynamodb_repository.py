from typing import Optional, Iterator, Type, Dict, Any, Final
from src.shared.adapters.persistence import commons
from src.shared.adapters.persistence.commons import E, I


#########################################################################################
#           DYNAMODB REPOSITORY                                                         #
#########################################################################################

MAX_DYNAMO_DB_BATCH_SIZE_PER_TRX = 100


class DynamoDbRepository(commons.Repository[E]):
    def __init__(
        self,
        session: commons.SessionDB,
        table_name: str,
        entity_type: Type[E],
    ) -> None:
        self._session = session
        self._table_name = table_name
        self._key_name: Final = "id._key"
        self._entity_type = entity_type

    @classmethod
    def _deserializer_item(cls, dynamodb_record: Dict[str, Any]) -> Dict[str, Any]:
        from boto3.dynamodb.types import TypeDeserializer

        deserializer = TypeDeserializer()
        parsed_record = {
            k: deserializer.deserialize(v) for k, v in dynamodb_record.items()
        }
        return parsed_record

    @classmethod
    def _serialize_entity(cls, entity: E) -> Dict[str, Any]:
        from decimal import Decimal

        nested_dict = entity.model_dump()
        for k, v in nested_dict.items():
            if isinstance(v, Decimal):
                nested_dict[k] = float(v)
        return nested_dict

    def put(self, item: E) -> None:
        self._session.add_write_operation(
            operation=self._build_write_operation(
                item=item, operation_type=_DynamoDbPutOperation
            )
        )

    def update(self, item: E) -> None:
        self._session.add_write_operation(
            operation=self._build_write_operation(
                item=item, operation_type=_DynamoDbUpdateOperation
            )
        )

    def _build_write_operation(
        self,
        item: E,
        operation_type: Type["_DynamoDbWriteOperation"],
    ) -> "_DynamoDbWriteOperation":
        # In case of error we don't update the real item in memory
        item_to_save = item.copy()
        item_to_save._increase_version()
        record_serialized = self._serialize_entity(item_to_save)
        record_serialized[self._key_name] = item_to_save.id._key()
        return operation_type(
            table_name=self._table_name,
            key_name=self._key_name,
            entity_dict=record_serialized,
        )

    def get_by_id(self, id: I) -> E:
        item = self._session.client.get_item(
            TableName=self._table_name, Key={self._key_name: {"S": id._key()}}
        ).get("Item")
        if item:
            item_deserialized = self._deserializer_item(dynamodb_record=item)
            print(f"Item result: {item_deserialized}")
            return self._entity_type.parse_obj(item_deserialized)
        raise ValueError(f"Item with id {id._key()} not found")

    def find_by_id(self, id: I) -> Optional[E]:
        try:
            return self.get_by_id(id=id)
        except ValueError:
            return None

    def get_all(self) -> Iterator[E]:
        params = {
            "TableName": self._table_name,
            "Limit": MAX_DYNAMO_DB_BATCH_SIZE_PER_TRX,
        }
        while True:
            response = self._session.client.scan(**params)
            items = response.get("Items", [])
            for item in items:
                yield self._entity_type.parse_obj(item)

            if "LastEvaluatedKey" in response:
                params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            else:
                break


############## DYNAMO DB WRITE OPERATION IN DB COMPONENTS ####################################################
class DuplicateWriteOperationsError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "A single write operation for each entity is allowed in the same context"
        )


class DynamoBatchSizePerTrxExceedsError(Exception):
    def __init__(self) -> None:
        super().__init__("DynamoDB only allows 100 operations in a single transaction")


class WrongProcessTransactionTypeSelectedError(Exception):
    ...


class TransactionFailedError(Exception):
    ...


class _DynamoDbWriteOperation(commons.WriteOperation):
    def __init__(
        self, table_name: str, key_name: str, entity_dict: Dict[str, Any]
    ) -> None:
        self._table_name = table_name
        self._key_name = key_name
        self._id = entity_dict.get(key_name)
        self._entity = entity_dict

    @property
    def id(self) -> str:
        return self._id  # type: ignore

    @property
    def key_name(self) -> str:
        return self._key_name

    @property
    def table_name(self) -> str:
        return self._table_name

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
    def entity_serialized(self) -> Dict[str, Any]:
        entity_dict = super().entity_serialized
        return {
            "Put": {
                "Item": entity_dict,
                "TableName": self.table_name,
                "ConditionExpression": "attribute_not_exists(#id)",
                "ExpressionAttributeNames": {"#id": self.key_name},
                "ReturnValuesOnConditionCheckFailure": "ALL_OLD",
            }
        }


class _DynamoDbUpdateOperation(_DynamoDbWriteOperation):
    def __init__(
        self, table_name: str, key_name: str, entity_dict: Dict[str, Any]
    ) -> None:
        super().__init__(table_name, key_name, entity_dict)

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
