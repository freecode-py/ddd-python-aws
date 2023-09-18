from src.shared import base_types


class CreateCompany(base_types.Command):
    name: str
    address: str
    country: str
