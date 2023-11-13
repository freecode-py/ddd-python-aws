import pydantic
from src.company.service import commands, exceptions
from src.shared.adapters import repository, unit_of_work, event_publisher
from src.company.domain import aggregate


class Settings(pydantic.BaseSettings):
    aggregate_company_table_name: str
    aggregate_company_table_key_name: str


def company_repository_instance(
    uow: unit_of_work.UnitOfWork,
) -> repository.DynamoDbRepository:
    _SETTINGS = Settings()
    return repository.DynamoDbRepository(
        uow=uow,
        table_name=_SETTINGS.aggregate_company_table_name,
        key_name=_SETTINGS.aggregate_company_table_key_name,
        entity_type=aggregate.Company,
    )


def create_new_company(uow: unit_of_work.UnitOfWork, input: commands.CreateCompany):
    company = aggregate.Company.create(**input.dict())
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


def get_company_by_id(uow: unit_of_work.UnitOfWork, input: str):
    id = aggregate.CompanyId(value=input)
    company_repository = company_repository_instance(uow=uow)
    company = company_repository.get_by_id(id=id)
    return company
