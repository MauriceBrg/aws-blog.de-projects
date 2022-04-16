from typing import Any

# We expect events in this form:
# {"return": "failure|success"}
def lambda_handler(event: dict, context: Any) -> dict:
    
    if event.get("return", "failure") == "failure":
        # By default we return a failure
        raise RuntimeError("I'm supposed to fail here")
    else:
        return {"this_invocation": "was_successful"}
