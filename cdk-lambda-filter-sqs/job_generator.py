import time

import boto3

NUM_EVENTS = 20

TABLE_NAME = "sqs-filter-demo-data"
QUEUE_NAME = "sqs-filter-demo-queue"


def main():

    sqs_client = boto3.client("sqs")

    queue_url = sqs_client.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]

    table = boto3.resource("dynamodb").Table(TABLE_NAME)
    queue = boto3.resource("sqs").Queue(queue_url)

    print("Removing summary item from table")
    try:
        table.delete_item(Key={"PK": "SUMMARY"})
    except Exception as err:
        print(f"Got {err} - the table is already empty")
    
    print("Purging Queue")
    sqs_client.purge_queue(QueueUrl=queue_url)
    print("Purging queues can take up to 60 seconds, waiting...")
    time.sleep(1)

    for count in range(NUM_EVENTS):

        print(f"Sending Message Group {count + 1} with 2 messages")
        queue.send_messages(
            Entries=[
                {
                    "Id": "1",
                    "MessageBody": "Destined for Lambda",
                    "MessageAttributes": {
                        "process_with_lambda": {
                            "StringValue": "1",
                            "DataType": "String"
                        }
                    }
                },
                {
                    "Id": "2",
                    "MessageBody": "Not for Lambda",
                },
            ]
        )

        time.sleep(.5)


if __name__ == "__main__":
    main()
