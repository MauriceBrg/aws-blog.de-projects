import time

from datetime import datetime
import boto3

from job_generator import QUEUE_NAME, TABLE_NAME

QUERY_INTERVAL_IN_SECONDS = 15

ATTRIBUTES = ["views", "duration", "likes", "dislikes"]

TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
DYNAMODB = boto3.resource("dynamodb")

TABLE_CELL_WIDTH = 10

def get_counter_value():
    
    response = TABLE.get_item(Key={"PK":"SUMMARY"})

    try:
        return response["Item"]["counter"]
    except KeyError:
        return 0

def count_remaining_messages_in_queue():
    
    sqs_client = boto3.client("sqs")
    queue_url = sqs_client.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]

    queue = boto3.resource("sqs").Queue(queue_url)

    counter = 0

    more_messages = True
    while more_messages:

        more_messages = False
        messages = queue.receive_messages(MaxNumberOfMessages=10)

        # Remove messages from the Queue
        for message in messages:
            message.delete()

        counter += len(messages)
        if len(messages) > 0:
            more_messages = True

        # Wait a little
        time.sleep(5)
    
    return counter

def main():

    table_counter = get_counter_value()
    print(f"Lambda processed {table_counter} records")

    queue_counter = count_remaining_messages_in_queue()
    print(f"The Queue contained {queue_counter} messages")

if __name__ == "__main__":
    main()
