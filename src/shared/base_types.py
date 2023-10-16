import enum
import decimal
import pydantic
import uuid
import time
import functools
import copy
from typing import Dict, Any, Iterator, List, Callable


class NamedEnum(str, enum.Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name


class UUIDGenerator:
    @staticmethod
    def uuid() -> str:
        return str(uuid.uuid4())


class ValueObject(pydantic.BaseModel):
    class Config:
        frozen = True
        extra = pydantic.Extra.ignore
        json_encoders = {
            decimal.Decimal: str,
        }


class EpochTime(ValueObject):
    time_ns: int

    def __str__(self) -> str:
        return str(self.time_ns)

    def __lt__(self, epoch_time: "EpochTime") -> bool:
        return self.time_ns < epoch_time.time_ns

    def __le__(self, epoch_time: "EpochTime") -> bool:
        return self.time_ns <= epoch_time.time_ns

    def __eq__(self, epoch_time: "EpochTime") -> bool:
        return self.time_ns == epoch_time.time_ns

    def __gt__(self, epoch_time: "EpochTime") -> bool:
        return self.time_ns > epoch_time.time_ns

    def __ge__(self, epoch_time: "EpochTime") -> bool:
        return self.time_ns >= epoch_time.time_ns

    @staticmethod
    def now() -> "EpochTime":
        return EpochTime(time_ns=time.time_ns())


def update_last_udpate_date(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.last_update = EpochTime.now()
        return result

    return wrapper


class Key(ValueObject):
    class MalformedError(Exception):
        def __init__(self) -> None:
            super().__init__(
                "Key only support primitives types. None value is not allowed"
            )

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        attr_dict = super().dict(**kwargs)
        return attr_dict

    def _key(self, **kwargs: Dict[str, Any]) -> str:
        attrs_dict = super().dict(**kwargs)

        def values(attrs_dict: Dict[str, Any]) -> Iterator[str]:
            for v in attrs_dict.values():
                if not v or not isinstance(
                    v, (str, int, float, decimal.Decimal, enum.Enum)
                ):
                    raise EntityId.MalformedError()
                yield str(v.value if isinstance(v, enum.Enum) else v)

        return "#".join(values(attrs_dict=attrs_dict))


class EntityId(Key):
    ...


class Entity(pydantic.BaseModel):
    id: "EntityId"

    class Config:
        extra = pydantic.Extra.ignore
        json_encoders = {
            decimal.Decimal: str,
        }


class RootEntity(Entity):
    created: EpochTime = pydantic.Field(default_factory=EpochTime.now)
    last_update: EpochTime = pydantic.Field(default_factory=EpochTime.now)
    version: int = pydantic.Field(default=0)

    def _increase_version(self):
        self.version += 1

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        attr_dict = super().dict(**kwargs)
        return attr_dict


class DomainAggregate(RootEntity):
    _events: List["DomainEvent"]

    @property
    def events(self) -> List["DomainEvent"]:
        return self._events

    def add_event(self, event: "DomainEvent"):
        self._events.append(event)

    def pull_events(self) -> List["DomainEvent"]:
        events = copy.copy(self._events)
        self._events.clear()
        return events


class RepositoryAggregate(RootEntity):
    ...


class Projection(DomainAggregate):
    ...


class Command(ValueObject):
    ...


class DomainEvent(ValueObject):
    id: str = pydantic.Field(default_factory=UUIDGenerator.uuid)
    created: EpochTime = pydantic.Field(default_factory=EpochTime.now)
    domain_name: str


def split_list(input_list: List[Any], chunk_size: int) -> Iterator[Any]:
    """Split list in N chunk size. Finally return iterator with the result"""
    if chunk_size <= 0:
        raise ValueError("Chunk size must be bigger than zero")
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i : i + chunk_size]


class Country(NamedEnum):
    USA = enum.auto()
    ARG = enum.auto()
    DOM = enum.auto()
    CO = enum.auto()
