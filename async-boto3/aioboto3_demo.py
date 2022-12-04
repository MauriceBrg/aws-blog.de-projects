"""Demo for aioboto3."""
import asyncio
import base64
import collections
import json
import logging
import sys
import time
import typing

import aioboto3

LAMBDA_NAME = "LambdaDemo"

LOGGER = logging.getLogger(__name__)


async def format_error(configuration_identifier: str, response: dict):
    """Takes a configuration identifier and a lambda response and formats the error in the log"""
    LOGGER.error("Configuration %s FAILED the system test", configuration_identifier)
    LOGGER.error("The error message is: %s", response["FunctionError"])
    LOGGER.error(
        "%s Log output %s",
        "=" * 30,
        "=" * 30,
    )
    LOGGER.error(
        base64.b64decode(response["LogResult"].encode("utf-8")).decode("utf-8")
    )
    LOGGER.error(
        "%s End of log %s",
        "=" * 30,
        "=" * 30,
    )


async def run_system_test(configuration_identifier: str) -> bool:
    """Invoke the lambda function with the configuration identifier and parse the result"""

    session = aioboto3.Session()

    async with session.client("lambda") as lambda_client:

        response = await lambda_client.invoke(
            FunctionName=LAMBDA_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(
                {
                    "configuration_identifier": configuration_identifier,
                    "system_test": True,
                }
            ),
            LogType="Tail",
        )

    if "FunctionError" in response:
        await format_error(configuration_identifier, response)
        return False

    LOGGER.info("Configuration %s PASSED the system test", configuration_identifier)
    payload: dict = json.loads(await response["Payload"].read())
    LOGGER.debug("Payload %s", json.dumps(payload))

    return payload.get("system_test_successful", False)


async def run_system_test_for_configurations(
    configuration_identifiers: typing.List[str],
) -> typing.List[bool]:
    """Schedules system tests for all configurations and waits until they'r done."""

    return await asyncio.gather(
        *[
            run_system_test(config_identifier)
            for config_identifier in configuration_identifiers
        ]
    )


def main():
    """Generates configurations for the system test, triggers it and reports the result."""

    LOGGER.addHandler(logging.StreamHandler(sys.stdout))
    LOGGER.setLevel(logging.INFO)

    configuration_identifiers = [f"config_{n}" for n in range(40)]

    start_time = time.perf_counter()
    results = asyncio.run(run_system_test_for_configurations(configuration_identifiers))
    runtime_in_s = time.perf_counter() - start_time

    LOGGER.info("The system test took %.3fs", runtime_in_s)

    counts = collections.Counter(results)
    LOGGER.info(
        "%s of %s passed the test - %s failed",
        counts[True],
        len(configuration_identifiers),
        counts[False],
    )


if __name__ == "__main__":
    main()

