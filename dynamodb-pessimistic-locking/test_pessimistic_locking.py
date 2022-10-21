# pylint: disable=redefined-outer-name,unused-argument
import time

import boto3
import moto
import pytest


from dynamodb_pessimistic_locking import (
    acquire_lock,
    release_lock,
    TABLE_NAME,
)


def create_table_if_not_exists():

    client = boto3.client("dynamodb")

    try:
        client.create_table(
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        boto3.resource("dynamodb").Table(TABLE_NAME).wait_until_exists()
    except client.exceptions.ResourceInUseException:
        pass


@pytest.fixture
def existing_table():
    """Provides a dynamodb table for the lock in moto."""
    with moto.mock_dynamodb():
        create_table_if_not_exists()
        yield


@moto.mock_dynamodb()
def test_that_a_table_gets_created():
    """Assert the table gets created."""

    # Arrange

    # Act
    create_table_if_not_exists()

    # Assert
    assert boto3.resource("dynamodb").Table(TABLE_NAME).table_name == TABLE_NAME


def test_that_it_supports_pre_existing_tables(existing_table):
    """Assert we don't throw a tantrum/exception if the table already exists."""

    # Arrange

    # Act
    create_table_if_not_exists()

    # Assert
    # well, nothing really


def test_that_a_lock_can_be_acquired_if_none_exists(existing_table):
    """
    Assert that a lock can be acquired if there is no pre-existing lock
    """

    # Arrange

    # Act
    is_locked = acquire_lock("resource", 5, "tx-1")

    # Assert
    assert is_locked


def test_that_a_lock_can_be_acquired_if_the_old_is_expired(existing_table):
    """
    Assert that a lock can be acquired if the pre-existing lock is expired.
    """

    # Arrange
    acquire_lock("resource", 1, "tx-1")
    time.sleep(2)

    # Act
    is_locked = acquire_lock("resource", 5, "tx-1")

    # Assert
    assert is_locked


def test_that_a_lock_is_rejected_if_another_exists(existing_table):
    """
    Assert that no lock is granted if the resource is already locked.
    """

    # Arrange
    acquire_lock("resource", 10, "tx-1")

    # Act
    is_locked = acquire_lock("resource", 5, "tx-1")

    # Assert
    assert not is_locked


def test_that_a_lock_can_be_release_with_the_tx_id(existing_table):
    """
    Assert that a lock can be released if we know its transaction id.
    """

    # Arrange
    acquire_lock("resource", 10, "tx-1")

    # Act
    lock_released = release_lock("resource", "tx-1")

    # Assert
    assert lock_released
    assert acquire_lock("resource", 15, "tx-2")


def test_that_a_lock_cant_be_released_that_doesnt_exist(existing_table):
    """
    Assert that a non-existent lock can't be released.
    """

    # Arrange

    # Act
    lock_released = release_lock("resource", "nx-tx")

    # Assert
    assert not lock_released


def test_that_a_lock_cant_be_released_if_the_tx_doesnt_match(existing_table):
    """
    Assert that releasing a lock fails if we use an incorrect transaction id.
    """

    # Arrange
    acquire_lock("resource", 10, "secret-tx")

    # Act
    lock_released = release_lock("resource", "unsuccessful-guess")

    # Assert
    assert not lock_released
