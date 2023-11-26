from typing import Protocol, Dict, Any, TypeVar, Optional, List, Iterator, NewType
from src.shared import base_types

E = TypeVar("E", bound=base_types.RepositoryAggregate)
I = TypeVar("I", bound=base_types.EntityId)


class WriteOperation(Protocol):
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


class SessionDB(Protocol):
    _batches: Dict[str, WriteOperation] = {}
    client: Any

    def add_write_operation(self, operation: WriteOperation) -> None:
        ...

    def clear_batches(self) -> None:
        ...

    def execute_in_single_transaction(self) -> None:
        ...

    def execute_in_batch_transaction(self) -> None:
        ...


class Repository(Protocol[E]):
    def put(self, item: E) -> None:
        ...

    def get_by_id(self, id: I) -> E:
        ...

    def find_by_id(self, id: I) -> Optional[E]:
        ...

    def get_all(self) -> Iterator[E]:
        ...
