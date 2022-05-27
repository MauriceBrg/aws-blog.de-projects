# DynamoDB Streamgazer

Read the [companion article first](https://aws-blog.de/2022/05/getting-a-near-real-time-view-of-a-dynamodb-stream-with-python.html)

## Install

Install the dependencies `pip install -r requirements`.

## Usage

```terminal
$ python dynamodb_streamgazer.py -h
usage: dynamodb_streamgazer.py [-h] [--print-record] [--print-summary] stream_arn

See what's going on in DynamoDB Streams in near real-time 🔍

positional arguments:
  stream_arn            The ARN of the stream you want to watch.

optional arguments:
  -h, --help            show this help message and exit
  --print-record, -pr   Print each change record. If nothing else is selected, this is the default.
  --print-summary, -ps  Print a summary of a change record
```

## Example
```terminal
python dynamodb_streamgazer.py $STREAM_ARN --print-summary --print-record
Starting watcher for shard: shardId-00000001653646993166-46aa7561
Starting watcher for shard: shardId-00000001653648537152-e0a56e69
Starting watcher for shard: shardId-00000001653648750475-f3978e9b
Starting watcher for shard: shardId-00000001653657153330-46f0ba41
{'eventID': '13632bb66cf8c76f61ab676f7d2e9f07', 'eventName': 'INSERT', 'eventVersion': '1.1', 'eventSource': 'aws:dynamodb', 'awsRegion': 'eu-central-1', 'dynamodb': {'ApproximateCreationDateTime': datetime.datetime(2022, 5, 27, 15, 35, 57, tzinfo=tzlocal()), 'Keys': {'PK': {'S': 'test'}, 'SK': {'S': 'item'}}, 'NewImage': {'PK': {'S': 'test'}, 'SK': {'S': 'item'}}, 'SequenceNumber': '2119225400000000025318847566', 'SizeBytes': 24, 'StreamViewType': 'NEW_AND_OLD_IMAGES'}}
[2022-05-27T15:35:57+02:00] - INSERT - PK=test, SK=item
{'eventID': '0ad8ac37a29e125986efdd2b90477b94', 'eventName': 'MODIFY', 'eventVersion': '1.1', 'eventSource': 'aws:dynamodb', 'awsRegion': 'eu-central-1', 'dynamodb': {'ApproximateCreationDateTime': datetime.datetime(2022, 5, 27, 15, 36, 13, tzinfo=tzlocal()), 'Keys': {'PK': {'S': 'test'}, 'SK': {'S': 'item'}}, 'NewImage': {'PK': {'S': 'test'}, 'SK': {'S': 'item'}, 'new': {'S': 'Attribute'}}, 'OldImage': {'PK': {'S': 'test'}, 'SK': {'S': 'item'}}, 'SequenceNumber': '2119225500000000025318861946', 'SizeBytes': 48, 'StreamViewType': 'NEW_AND_OLD_IMAGES'}}
[2022-05-27T15:36:13+02:00] - MODIFY - PK=test, SK=item
{'eventID': '5de35850775ca9751df37a3a7ac51ef1', 'eventName': 'REMOVE', 'eventVersion': '1.1', 'eventSource': 'aws:dynamodb', 'awsRegion': 'eu-central-1', 'dynamodb': {'ApproximateCreationDateTime': datetime.datetime(2022, 5, 27, 15, 36, 23, tzinfo=tzlocal()), 'Keys': {'PK': {'S': 'test'}, 'SK': {'S': 'item'}}, 'OldImage': {'PK': {'S': 'test'}, 'SK': {'S': 'item'}, 'new': {'S': 'Attribute'}}, 'SequenceNumber': '2119225600000000025318872157', 'SizeBytes': 36, 'StreamViewType': 'NEW_AND_OLD_IMAGES'}}
[2022-05-27T15:36:23+02:00] - REMOVE - PK=test, SK=item
```
