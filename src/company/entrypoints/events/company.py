from src.company.service import commands, company as services
from src.shared.adapters import unit_of_work
from typing import Dict, Any


def handler(event: Dict[str, Any], context: Any) -> None:
    try:
        print("Testing event bridge")
        print(event)
    except Exception as ex:
        print(ex)
        raise
