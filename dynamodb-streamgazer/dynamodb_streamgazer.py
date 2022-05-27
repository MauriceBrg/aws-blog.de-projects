#! /usr/bin/env python
import argparse
import collections
import multiprocessing as mp
import time
import typing

from datetime import datetime

import boto3

Shard = collections.namedtuple(
    typename="Shard",
    field_names=[
        "stream_arn",
        "shard_id",
        "parent_shard_id",
        "starting_sequence_number",
        "ending_sequence_number"
    ]
)

def list_all_shards(stream_arn: str, **kwargs: dict) -> typing.List[Shard]:

    def _shard_response_to_shard(response: dict) -> Shard:
        return Shard(
            stream_arn=stream_arn,
            shard_id=response.get("ShardId"),
            parent_shard_id=response.get("ParentShardId"),
            starting_sequence_number=response.get("SequenceNumberRange", {}).get("StartingSequenceNumber"),
            ending_sequence_number=response.get("SequenceNumberRange", {}).get("EndingSequenceNumber")
        )
 
    client = boto3.client("dynamodbstreams")
    pagination_args = {}
    exclusive_start_shard_id = kwargs.get("next_page_identifier", None)
    if exclusive_start_shard_id is not None:
        pagination_args["ExclusiveStartShardId"] = exclusive_start_shard_id
    
    response = client.describe_stream(
        StreamArn=stream_arn,
        **pagination_args
    )

    list_of_shards = [_shard_response_to_shard(item) for item in response["StreamDescription"]["Shards"]]

    next_page_identifier = response["StreamDescription"].get("LastEvaluatedShardId")
    if next_page_identifier is not None:
        list_of_shards += list_all_shards(
            stream_arn=stream_arn,
            next_page_identifier=next_page_identifier
        )
    
    return list_of_shards

def is_open_shard(shard: Shard) -> bool:
    return shard.ending_sequence_number is None

def list_open_shards(stream_arn: str) -> typing.List[Shard]:
    all_shards = list_all_shards(
        stream_arn=stream_arn
    )

    open_shards = [shard for shard in all_shards if is_open_shard(shard)]

    return open_shards

def get_shard_iterator(shard: Shard, iterator_type: str = "LATEST") -> str:
    client = boto3.client("dynamodbstreams")

    response = client.get_shard_iterator(
        StreamArn=shard.stream_arn,
        ShardId=shard.shard_id,
        ShardIteratorType=iterator_type
    )
    
    return response["ShardIterator"]

def get_next_records(shard_iterator: str) -> typing.Tuple[typing.List[dict], str]:
    client = boto3.client("dynamodbstreams")

    response = client.get_records(
        ShardIterator=shard_iterator
    )

    return response["Records"], response.get("NextShardIterator")

def shard_watcher(shard: Shard, callables: typing.List[typing.Callable], start_at_oldest = False):
    
    shard_iterator_type = "TRIM_HORIZON" if start_at_oldest else "LATEST"
    shard_iterator = get_shard_iterator(shard, shard_iterator_type)

    while shard_iterator is not None:
        records, shard_iterator = get_next_records(shard_iterator)

        for record in records:
            for handler in callables:
                handler(record)
        
        time.sleep(0.5)

def start_watching(stream_arn: str, callables: typing.List[typing.Callable]) -> None:

    shard_to_watcher: typing.Dict[str, mp.Process] = {}
    initial_loop = True

    while True:

        open_shards = list_open_shards(stream_arn=stream_arn)
        start_at_oldest = True
        if initial_loop:
            start_at_oldest = False
            initial_loop = False

        for shard in open_shards:
            if shard.shard_id not in shard_to_watcher:

                print("Starting watcher for shard:", shard.shard_id)
                args = (shard, callables, start_at_oldest)
                process = mp.Process(target=shard_watcher, args=args)
                shard_to_watcher[shard.shard_id] = process
                process.start()
                
        time.sleep(10)

def print_summary(change_record: dict):

    changed_at:datetime = change_record["dynamodb"]["ApproximateCreationDateTime"]
    event_type:str = change_record["eventName"]

    item_keys:dict = change_record["dynamodb"]["Keys"]
    item_key_list = []
    for key in sorted(item_keys.keys()):
        value = item_keys[key][list(item_keys[key].keys())[0]]
        item_key_list.append(f"{key}={value}")
    
    output_str = "[{0}] - {1:^6} - {2}".format(changed_at.isoformat(timespec="seconds"), event_type, ", ".join(item_key_list))

    print(output_str)

def print_change_record(change_record: dict):
    print(change_record)

def main():

    parser = argparse.ArgumentParser(description="See what's going on in DynamoDB Streams in near real-time 🔍")
    parser.add_argument("stream_arn", type=str, help="The ARN of the stream you want to watch.")
    parser.add_argument("--print-record", "-pr", action="store_true", help="Print each change record. If nothing else is selected, this is the default.")
    parser.add_argument("--print-summary", "-ps", action="store_true", help="Print a summary of a change record")
    parsed = parser.parse_args()

    handlers = []
    if parsed.print_record:
        handlers.append(print_change_record)
    if parsed.print_summary:
        handlers.append(print_summary)
    
    if len(handlers) == 0:
        # When no handlers are set, we default to printing the record
        handlers.append(print_change_record)

    start_watching(parsed.stream_arn, handlers)

if __name__ == "__main__":
    main()

