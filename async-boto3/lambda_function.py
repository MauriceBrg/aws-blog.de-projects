import random
import time

def lambda_handler(event, context):
    print(event)
    sleep_time = random.randint(1, 10)
    print(f"Sleeping for {sleep_time}s")
    time.sleep(sleep_time)
    
    if random.randint(1, 100) <= 15:
        # 15% chance of errors
        raise ValueError("Something went wrong!")
    
    return {
        "configuration_identifier": event.get("configuration_identifier"),
        "slept_for": sleep_time,
        "system_test_successful": True
    }
