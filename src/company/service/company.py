from src.company.service import commands, exceptions
from src.shared import base_types
from src.shared.adapters import unit_of_work, event_publisher
from src.company.domain import aggregate
from src.shared.adapters.persistence import dynamodb_repository


class Settings(base_types.Settings):
    aggregate_company_table_name: str


def company_repository_instance(
    uow: unit_of_work.UnitOfWork,
) -> dynamodb_repository.DynamoDbRepository:
    _SETTINGS = Settings()  # type: ignore
    return dynamodb_repository.DynamoDbRepository(
        session=uow.session,
        table_name=_SETTINGS.aggregate_company_table_name,
        entity_type=aggregate.Company,
    )


def create_new_company(
    uow: unit_of_work.UnitOfWork, input: commands.CreateCompany
) -> None:
    company = aggregate.Company.create(**input.model_dump())
    company_repository = company_repository_instance(uow=uow)
    if company_repository.find_by_id(id=company.id):
        raise exceptions.CompanyAlredyExistError(
            f"Company {company.id.value} already exist"
        )

    with uow.transaction():
        company_repository.put(item=company)
    events = company.pull_events()
    _message_bus_client = event_publisher.EventBridgePublisher()
    print(f"Events to publish: [{len(events)}]")
    _message_bus_client.publish(events=events)
    print("Company was saved successfuly")


def get_company_by_id(uow: unit_of_work.UnitOfWork, input: str) -> aggregate.Company:
    id = aggregate.CompanyId(value=input)
    company_repository = company_repository_instance(uow=uow)
    company: aggregate.Company = company_repository.get_by_id(id=id)
    return company
