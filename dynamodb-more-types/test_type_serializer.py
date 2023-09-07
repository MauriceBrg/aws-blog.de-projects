"""
Implementation of a boto3 DynamoDB Table Resource that's able to store
and retrieve Python Floats and Datetime object.

requirements.txt:

boto3
moto
pytest
"""
# pylint: disable=redefined-outer-name,unused-argument
import typing

from collections.abc import Set
from datetime import datetime

import boto3
import moto
import pytest

from boto3.dynamodb.transform import TransformationInjector
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

TEST_USING_IN_MEMORY_TABLE_FIXTURE: bool = True


class CustomSerializer(TypeSerializer):  # pylint: disable=too-few-public-methods
    """
    Thin wrapper around the original TypeSerializer that teaches it to:
    - Serialize datetime objects as ISO8601 strings and stores them as binary info.
    - Serialize float objects as strings and stores them as binary info.
    - Deal with the above as part of sets
    """

    def _serialize_datetime(self, value) -> typing.Dict[str, bytes]:
        return {"B": f"DT:{value.isoformat(timespec='microseconds')}".encode("utf-8")}

    def _serialize_float(self, value) -> typing.Dict[str, bytes]:
        return {"B": f"FL:{str(value)}".encode("utf-8")}

    def serialize(self, value) -> typing.Dict[str, typing.Any]:
        try:
            return super().serialize(value)
        except TypeError as err:
            # If the value is of type datetime, encode it as a binary
            if isinstance(value, datetime):
                return self._serialize_datetime(value)

            # If the value is of type float, encode it as a binary
            if isinstance(value, float):
                return self._serialize_float(value)

            # Special case for sets as the original implementation does type checking for elements
            if isinstance(value, Set):
                return {
                    "BS": [
                        self.serialize(v)["B"]  # We need to extract the bytes
                        for v in value
                    ]
                }

            # A type that the reference implementation and we can't handle
            raise err


class CustomDeserializer(TypeDeserializer):  # pylint: disable=too-few-public-methods
    """
    Thin wrapper around the original TypeDeserializer that teaches it to:
    - Deserialize datetime objects from specially encoded binary data.
    - Deserialize float objects from specially encoded binary data.
    """

    def _deserialize_b(self, value: bytes):
        """
        Overwrites the private method to deserialize binary information.
        """
        if value[:3].decode("utf-8") == "DT:":
            return datetime.fromisoformat(value.decode("utf-8").removeprefix("DT:"))
        if value[:3].decode("utf-8") == "FL:":
            return float(value.decode("utf-8").removeprefix("FL:"))

        return super()._deserialize_b(value)


class CustomTransformationInjector(TransformationInjector):
    """
    Thin wrapper around the Transformation Injector that uses
    our serializer/deserializer.
    """

    def __init__(
        self,
        transformer=None,
        condition_builder=None,
        serializer=None,
        deserializer=None,
    ):
        super().__init__(
            transformer, condition_builder, CustomSerializer(), CustomDeserializer()
        )


def build_boto_session() -> boto3.Session:
    """
    Build a session object that replaces the DynamoDB serializers.

    NOTE: It's important that the registration/unregistration
          happens before any resource or client is instantiated
          from the session as those are copied based on the
          state of the session at the time of instantiating
          the client/resource.
    """
    session = boto3.Session()

    # Unregister the default Serializer
    session.events.unregister(
        event_name="before-parameter-build.dynamodb",
        unique_id="dynamodb-attr-value-input",
    )

    # Unregister the default Deserializer
    session.events.unregister(
        event_name="after-call.dynamodb",
        unique_id="dynamodb-attr-value-output",
    )

    injector = CustomTransformationInjector()

    # Register our own serializer
    session.events.register(
        "before-parameter-build.dynamodb",
        injector.inject_attribute_value_input,
        unique_id="dynamodb-attr-value-input",
    )

    # Register our own deserializer
    session.events.register(
        "after-call.dynamodb",
        injector.inject_attribute_value_output,
        unique_id="dynamodb-attr-value-output",
    )

    return session


@pytest.fixture
def table_fixture():
    """
    Creates an in-memory moto DynamoDB table instead of running
    the tests against AWS. This only happens if
    TEST_USING_IN_MEMORY_TABLE_FIXTURE = True.
    """
    if TEST_USING_IN_MEMORY_TABLE_FIXTURE:
        with moto.mock_dynamodb():
            boto3.client("dynamodb").create_table(
                AttributeDefinitions=[
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                ],
                TableName="data",
                KeySchema=[
                    {
                        "AttributeName": "PK",
                        "KeyType": "HASH",
                    },
                    {
                        "AttributeName": "SK",
                        "KeyType": "RANGE",
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            yield
    else:
        # Test against the real DynamoDB service
        yield None


def test_that_we_can_store_and_read_datetimes_in_dynamodb(table_fixture):
    """
    Test that we can store an item with a datetime object
    in it and retrieve it at a later time with the attribute
    still being of type datetime.
    """
    # Arrange
    tbl = build_boto_session().resource("dynamodb").Table("data")
    item_with_datetime_data = {
        "PK": "item_with",
        "SK": "datetime_data",
        "binary_data": "Hello World!".encode(),  # To ensure we don't break binary storage
        "datetime": datetime.fromisoformat("2023-05-05T10:10:10.123456+05:00"),
    }

    # Act
    tbl.put_item(Item=item_with_datetime_data)

    item_from_ddb = tbl.get_item(Key={"PK": "item_with", "SK": "datetime_data"})["Item"]

    # Assert
    assert item_with_datetime_data == item_from_ddb
    assert isinstance(item_from_ddb["datetime"], datetime)


def test_that_we_can_store_and_read_floats_in_dynamodb(table_fixture):
    """
    Test that we can store an item with a float object
    in it and retrieve it at a later time with the attribute
    still being of type float.
    """
    # Arrange
    tbl = build_boto_session().resource("dynamodb").Table("data")
    item_with_float_data = {
        "PK": "item_with",
        "SK": "float_data",
        "binary_data": "Hello World!".encode(),  # To ensure we don't break binary storage
        "pi": 3.14159265359,  # yes, there's more
    }

    # Act
    tbl.put_item(Item=item_with_float_data)

    item_from_ddb = tbl.get_item(Key={"PK": "item_with", "SK": "float_data"})["Item"]

    # Assert
    assert item_with_float_data == item_from_ddb
    assert isinstance(item_from_ddb["pi"], float)


def test_that_we_can_store_nested_stuff_in_dynamodb(table_fixture):
    """
    Test that we can store an item with a float object
    in it and retrieve it at a later time with the attribute
    still being of type float.
    """
    # Arrange
    tbl = build_boto_session().resource("dynamodb").Table("data")
    item_with_nested_data = {
        "PK": "item_with",
        "SK": "deeply_nested",
        "binary_data": "Hello World!".encode(),  # To ensure we don't break binary storage
        "set_of_floats": {3.14159265359, 1.618},
        "pi": 3.14159265359,  # yes, there's more
        "list_of_dates_floats_and_sets": [
            3.14159265359,
            datetime.fromisoformat("2022-01-01T00:00:00+00:00"),
            {3.14159265359, datetime.fromisoformat("2021-12-12T13:45:31+05:00")},
        ],
    }

    # Act
    tbl.put_item(Item=item_with_nested_data)

    item_from_ddb = tbl.get_item(Key={"PK": "item_with", "SK": "deeply_nested"})["Item"]

    # Assert
    assert item_with_nested_data == item_from_ddb


if __name__ == "__main__":
    # Only run the tests in this file if executed directly.
    pytest.main([__file__])

