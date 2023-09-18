from typing import Protocol, TypeVar, Optional, Iterator, Type, Dict, List, Any
from src.shared import base_types
from src.shared.adapters import unit_of_work


E = TypeVar("E", bound=base_types.RepositoryAggregate)
I = TypeVar("I", bound=base_types.EntityId)


class Repository(Protocol):
    def put(self, item: E) -> None:
        ...

    def get_by_id(self, id: I) -> E:
        ...

    def find_by_id(self, id: I) -> Optional[E]:
        ...

    def get_all(self) -> Iterator[E]:
        ...


class DynamoDbRepository:
    def __init__(
        self,
        uow: unit_of_work.UnitOfWork,
        table_name: str,
        key_name: str,
        entity_type: Type[E],
    ) -> None:
        self._uow = uow
        self._table_name = table_name
        self._key_name = key_name
        self._entity_type = entity_type

    def put(self, item: E) -> None:
        self._uow.add_put_operation(
            table_name=self._table_name, key_name=self._key_name, item=item
        )

    def get_by_id(self, id: I) -> E:
        return self._uow.get_item_by_id(
            table_name=self._table_name,
            key_name=self._key_name,
            id=id,
            entity_type=self._entity_type,
        )

    def find_by_id(self, id: I) -> Optional[E]:
        try:
            return self.get_by_id(id=id)
        except ValueError:
            return None

    def get_all(self) -> Iterator[E]:
        return self._uow.get_all_items(
            table_name=self._table_name, entity_type=self._entity_type
        )

    def find_by_gsi(self, gsi_name: str, gsi_key: str, gsi_value: str) -> Iterator[E]:
        ...
