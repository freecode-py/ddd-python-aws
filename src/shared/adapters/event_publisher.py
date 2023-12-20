import pydantic
import logging
import json
from typing import Protocol, List, TypeVar, Any, Dict, Type
from src.shared import base_types
import boto3
import backoff

_LOGGER = logging.Logger("Event publisher")
E = TypeVar("E", bound=base_types.DomainEvent)


class EventPublishError(Exception):
    ...


class EventPublisher(Protocol):
    def publish(self, events: List[E]) -> None:
        ...


class _CommonSettings(base_types.Settings):
    backoff_default_tries: int = pydantic.Field(default=3, env="BACKOFF_DEFAULT_TRIES")
    backoff_default_max_time: int = pydantic.Field(
        default=3, env="BACKOFF_DEFAULT_MAX_TIME"
    )


COMMON_SETTINGS = _CommonSettings()


class EventBridgePublisher:
    class _Settings(base_types.Settings):
        event_bridge_topic_arn: str = pydantic.Field(
            default="TO-FILL", env="EVENT_BRIDGE_TOPIC_ARN"
        )

    class EventBody(base_types.ValueObject):
        eventbus_name_arn: str = pydantic.Field(alias="EventBusName")
        source: str = pydantic.Field(
            alias="Source", description="Event Source. In our case (EventDomain source)"
        )
        detail_type: str = pydantic.Field(
            alias="DetailType",
            description="Event type. In our case we will use event class name",
        )
        detail: str = pydantic.Field(
            alias="Detail", description="Event parsed to json format"
        )

    def __init__(self) -> None:
        print("init eventbridge client")
        self._settings = EventBridgePublisher._Settings()
        self._client = boto3.client("events")

    @backoff.on_exception(
        backoff.fibo,
        EventPublishError,
        max_tries=COMMON_SETTINGS.backoff_default_tries,
        max_time=COMMON_SETTINGS.backoff_default_max_time,
    )
    def publish(self, events: List[E]) -> None:
        _LOGGER.info(f"EventBridge publisher. Events qty [{len(events)}]")
        if not events:
            _LOGGER.warning("No events provided. List passed is empty")
            return

        try:
            events_body_parsed = [
                self.convert_to_event_bridge_event(domain_event=event)
                for event in events
            ]
            response = self._put_events(events=events_body_parsed)
            _LOGGER.info(f"EVENT BRIDGE RESPONSE: {str(response)}")
            if response["FailedEntryCount"] == 0:
                _LOGGER.info("Events published successfuly ")
            else:
                entries_failed = response["Entries"]
                for entry in entries_failed:
                    if "ErrorCode" in entry:
                        _LOGGER.error(
                            f"Failed to publish event: {entry['ErrorCode']} - {entry['ErrorMessage']}"
                        )
                raise EventPublishError()
        except Exception as ex:
            _LOGGER.error("Error when try to publish event domain in Event Source")
            raise EventPublishError() from ex

    def convert_to_event_bridge_event(self, domain_event: E) -> Dict[str, Any]:
        return EventBridgePublisher.EventBody(
            EventBusName=self._settings.event_bridge_topic_arn,
            Source=domain_event.domain_name,
            DetailType=str(type(domain_event)),
            Detail=json.dumps(domain_event.model_dump()),
        ).model_dump(by_alias=True)

    def _put_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._client.put_events(Entries=events)  # type: ignore
