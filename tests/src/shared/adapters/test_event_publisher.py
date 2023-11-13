import pytest
from src.shared.adapters import event_publisher as publisher
from src.shared import base_types


class EventFakeCreated(base_types.DomainEvent):
    domain_name: str = "EventFake"


@pytest.fixture(scope="function")
def event_bridge_publisher() -> publisher.FakeEventBridgePublisher:
    return publisher.FakeEventBridgePublisher()


@pytest.mark.unittest
def test_should_not_publish_when_event_list_is_empty(
    event_bridge_publisher: publisher.FakeEventBridgePublisher,
) -> None:
    event_bridge_publisher.publish(events=[])
    assert event_bridge_publisher.events_published == []


@pytest.mark.unittest
def test_should_publish_events_successfuly(
    event_bridge_publisher: publisher.FakeEventBridgePublisher,
) -> None:
    import json

    fake_event = EventFakeCreated()
    event_bridge_publisher.publish(events=[fake_event])
    assert len(event_bridge_publisher.events_published) == 1
    event_published_dict = event_bridge_publisher.events_published[0]
    assert (
        event_published_dict["EventBusName"]
        == event_bridge_publisher._settings.event_bridge_topic_arn
    )
    assert event_published_dict["Source"] == fake_event.domain_name
    assert event_published_dict["DetailType"] == str(type(fake_event))
    assert event_published_dict["Detail"] == json.dumps(fake_event.dict())


# @pytest.mark.unittest
# def test_should_raise_EventPublishError_when_put_events_failed( event_bridge_publisher: publisher.FakeEventBridgePublisher, mocker) -> None:
#     ...
