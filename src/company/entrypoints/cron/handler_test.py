from src.company.service import commands, company as services
from src.shared.adapters import unit_of_work
from typing import Dict, Any


def handler(event: Dict[str, Any], context: Any):
    try:
        uow = unit_of_work.DynamoDbUnitOfWork()
        print("Test for create company")
        create_company_command = commands.CreateCompany(
            name=event["name"],
            address="test_address",
            country="USA",
        )
        print(create_company_command.dict())
        services.create_new_company(uow=uow, input=create_company_command)
    except Exception as ex:
        print(ex)
        raise


def handler_get_company(event: Dict[str, Any], context: Any):
    try:
        uow = unit_of_work.DynamoDbUnitOfWork()
        id = event["id"]
        company = services.get_company_by_id(uow=uow, input=id)
        print(company.dict())
    except Exception as ex:
        print(ex)
        raise
