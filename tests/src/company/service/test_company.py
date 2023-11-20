from src.company.service import commands, company as service
from src.shared.adapters import unit_of_work


# def test_create_company(uow: unit_of_work.FakeUnitOfWork) -> None:
#     request = commands.CreateCompany(
#         name="test",
#         address="test_address",
#         country="USA",
#     )
#     service.create_new_company(uow=uow, input=request)
#     assert True
