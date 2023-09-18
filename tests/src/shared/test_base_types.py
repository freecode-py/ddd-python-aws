import pytest
import mock
from typing import List
from src.shared import base_types


class FooId(base_types.EntityId):
    value: str


@pytest.mark.unittest
def test_should_UUIDGenerator_generate_uuid() -> None:
    assert isinstance(base_types.UUIDGenerator.uuid(), str)


@pytest.mark.unittest
def test_should_ValueObject_instace_inmutable() -> None:
    class Foo(base_types.ValueObject):
        a = 1

    foo = Foo()
    with pytest.raises(TypeError):
        foo.a = 2


class FooEntity(base_types.Entity):
    id: FooId


@pytest.mark.unittest
def test_should_Entity_ignore_extra_attrs() -> None:
    foo = FooEntity(id=FooId(value="test"))
    with pytest.raises(ValueError):
        foo.a = 1


class FooRootEntity(base_types.DomainAggregate):
    id: FooId
    _events: List[base_types.DomainEvent] = []


@pytest.mark.unittest
def test_should_RootEntity_instance_have_default_attrs() -> None:
    foo_root = FooRootEntity(id=FooId(value="test"))
    isinstance(foo_root.created, base_types.EpochTime)
    isinstance(foo_root.last_update, base_types.EpochTime)
    assert foo_root.version == 0


@pytest.mark.unittest
def test_should_RootEntity_increase_instance_version() -> None:
    foo_root = FooRootEntity(id=FooId(value="test"))
    foo_root._increase_version()
    assert foo_root.version > 0


@pytest.mark.unittest
def test_should_RootEntity_instance_add_events() -> None:
    foo_aggr = FooRootEntity(id=FooId(value="test"))
    assert foo_aggr.events == []
    foo_aggr.add_event(mock.MagicMock())
    assert len(foo_aggr.events) == 1


@pytest.mark.unittest
def test_should_EpochTime_now_method_instance() -> None:
    res = base_types.EpochTime.now()
    assert isinstance(res, base_types.EpochTime)
    assert isinstance(res.time_ns, int)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "input_list, chunk_size, result_expected",
    [
        ([], 2, []),
        ([1, 2, 3], 5, [[1, 2, 3]]),
        ([1, 2, 3], 3, [[1, 2, 3]]),
        ([1, 2, 3, 4, 5, 6], 2, [[1, 2], [3, 4], [5, 6]]),
        ([1, 2, 3, 4, 5, 6, 7], 3, [[1, 2, 3], [4, 5, 6], [7]]),
    ],
)
def test_should_split_list_successfuly(
    input_list: List, chunk_size: int, result_expected: List
) -> None:
    result = base_types.split_list(input_list, chunk_size)
    assert list(result) == result_expected


@pytest.mark.unittest
def test_split_list_negative_chunk_size_raise_error():
    input_list = [1, 2, 3, 4, 5]
    chunk_size = -2
    with pytest.raises(ValueError):
        list(base_types.split_list(input_list, chunk_size))
