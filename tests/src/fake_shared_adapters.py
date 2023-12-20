from typing import List, Dict, Any, Type, Tuple
from src.shared.adapters import unit_of_work, event_publisher
from src.shared.adapters.persistence import commons as persistence_commons


class FakeEventBridgePublisher(
    event_publisher.EventBridgePublisher, event_publisher.EventPublisher
):
    def __init__(self) -> None:
        super().__init__()
        self.events_published: List[Dict[str, Any]] = []

    def publish(self, events: List[event_publisher.E]) -> None:
        super().publish(events=events)

    def _put_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.events_published.extend(events)
        return {"FailedEntryCount": 0, "Entries": []}

    def is_event_type_was_published(self, event_type: Type[event_publisher.E]) -> bool:
        for e in self.events_published:
            if str(event_type) == e["DetailType"]:
                return True
        return False


class FakeDynamoDBClient:
    def __init__(self):
        self._data = {}

    def get_item(self, TableName: str, Key: Dict[str, Any]) -> Dict[str, Any]:
        table = self._data.get(TableName, {})
        key = self._deserializer_item(dynamodb_record=Key)
        item = table.get(key["id._key"], None)
        return {"Item": item} if item else {}

    def transact_write_items(self, TransactItems: Dict[str, Any]) -> None:
        for transact_item in TransactItems:
            if "Update" in transact_item:
                self._update_item(transact_item["Update"])
            elif "Put" in transact_item:
                self._put_item(transact_item["Put"])

    def _deserializer_item(cls, dynamodb_record: Dict[str, Any]) -> Dict[str, Any]:
        from boto3.dynamodb.types import TypeDeserializer

        deserializer = TypeDeserializer()
        parsed_record = {
            k: deserializer.deserialize(v) for k, v in dynamodb_record.items()
        }
        return parsed_record

    def _update_item(self, update_params: Dict[str, any]):
        table_name = update_params["TableName"]
        key = self._serialize_key(update_params["Key"])
        update_expression = update_params["UpdateExpression"]
        expression_attribute_values = update_params.get("ExpressionAttributeValues", {})

        table = self._data.setdefault(table_name, {})
        if key not in table:
            raise ValueError("Item does not exist for Update operation")

        item = table[key]

        # Evaluate update expression and update item
        for key, value in expression_attribute_values.items():
            update_expression = update_expression.replace(f":{key}", str(value))

        exec(update_expression, {"item": item})

    def _put_item(self, put_params):
        table_name = put_params["TableName"]
        item = put_params["Item"]
        record = self._deserializer_item(dynamodb_record=item)
        key = record["id._key"]

        self._data.setdefault(table_name, {})[key] = item


class FakeDynamoDBSession(
    unit_of_work.DefaultDynamoDBSession, persistence_commons.SessionDB
):
    def __init__(self) -> None:
        self._batches: Dict[str, persistence_commons.WriteOperation] = {}
        self.client = FakeDynamoDBClient()


class FakeDynamoDbUnitOfWork(unit_of_work.DynamoDbUnitOfWork):
    def __init__(self) -> None:
        super().__init__()
        self._message_bus_client = event_publisher.EventBridgePublisher()
        self._session = FakeDynamoDBSession()
