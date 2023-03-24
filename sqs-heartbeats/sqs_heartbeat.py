"""
Demo of an SQS Heartbeat / Dispatcher function.
"""
import logging
import random
import sys
import time

import boto3

LOGGER = logging.getLogger(__name__)

QUEUE_NAME = "test-queue"


def create_tasks_in_queue(queue_url, number_of_tasks_to_create) -> None:
    """
    Sends number_of_tasks_to_create to the queue.
    """

    sqs_res = boto3.resource("sqs")

    queue = sqs_res.Queue(queue_url)

    number_of_tasks_to_create = 3
    queue.send_messages(
        Entries=[
            {"Id": str(n), "MessageBody": f"Task #{n}"}
            for n in range(number_of_tasks_to_create)
        ]
    )
    LOGGER.info(
        "📮 Sent %s messages to the queue '%s'", number_of_tasks_to_create, QUEUE_NAME
    )


def is_successful(chance_in_percent: int) -> bool:
    """Returns true with a chance of chance_in_percent when called."""

    return random.choice(range(1, 101)) <= chance_in_percent


def processing_failed() -> bool:
    """
    This is where you'd determine if processing the message
    failed somehow, this could mean checking logs for errors,
    checking if a process is still running, ...
    """

    percent_chance_of_failure = 20
    return is_successful(percent_chance_of_failure)


def processing_completed() -> bool:
    """
    This is where your watchdog would check if the processing
    is completed, this may mean checking for files/ status entries
    in a database or whatever you come up with.
    """

    percent_chance_of_success = 50
    return is_successful(percent_chance_of_success)


def start_processing(message) -> None:
    """
    This is where you'd start the external/async processing of
    the message. It's important that this doesn't block the main
    thread, because this is where the watchdog/monitor lives.
    """
    LOGGER.info("🎬 Starting to process '%s'", message.body)


def monitor_processing_progress(sqs_message, visibility_timeout: int) -> bool:
    """
    Check if the message is still being processed or processing failed.
    Provide the heartbeat to SQS if it's still processing.
    """

    if processing_failed():
        LOGGER.info("💔 Processing of %s failed, retrying later.", sqs_message.body)
        return False

    if processing_completed():

        LOGGER.info("✅ Processing of %s complete!", sqs_message.body)
        sqs_message.delete()
        return True

    LOGGER.info("💓 Processing of %s still in progress", sqs_message.body)
    visibility_timeout += 5
    sqs_message.change_visibility(VisibilityTimeout=visibility_timeout)

    time.sleep(5)
    return monitor_processing_progress(sqs_message, visibility_timeout)


def main():
    """
    Main function that sends a few tasks to the queue and then
    processes them while monitoring the progress and sending
    heartbeats.
    """

    LOGGER.addHandler(logging.StreamHandler(sys.stdout))
    LOGGER.setLevel(logging.INFO)

    queue_url = boto3.client("sqs").get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]
    LOGGER.debug("Queue-URL: %s", queue_url)

    number_of_tasks_to_create = 3
    create_tasks_in_queue(queue_url, number_of_tasks_to_create)

    sqs_res = boto3.resource("sqs")
    queue = sqs_res.Queue(queue_url)

    messages_successfully_processed = 0

    while messages_successfully_processed < number_of_tasks_to_create:

        messages = queue.receive_messages(
            MaxNumberOfMessages=1,
            VisibilityTimeout=5,
            WaitTimeSeconds=5,
        )

        if messages:
            message = messages[0]

            LOGGER.info("📋 Got message '%s' from the queue", message.body)
            start_processing(message)

            result = monitor_processing_progress(message, visibility_timeout=5)
            messages_successfully_processed = (
                messages_successfully_processed + 1
                if result
                else messages_successfully_processed
            )
        else:
            LOGGER.info("Found no new messages...")


if __name__ == "__main__":
    main()

