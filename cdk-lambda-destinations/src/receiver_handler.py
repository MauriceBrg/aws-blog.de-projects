import json
from typing import Any

def lambda_handler(event: dict, context: Any) -> dict:
    print(json.dumps(event))
