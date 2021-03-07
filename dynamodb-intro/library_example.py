import string
import random
import typing

import boto3
import boto3.dynamodb.conditions as conditions

TABLE_NAME = "LibraryV2"
TABLE_RESOURCE = boto3.resource("dynamodb").Table(TABLE_NAME)

def create_table():
    ddb = boto3.client("dynamodb")
    ddb.create_table(
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"}
        ],
        TableName=TABLE_NAME,
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }
        ]
    )

def generate_sample_data():

    num_authors = 5
    num_books_per_author = 10

    for i in range(num_authors):

        author_name = f"author_{i}"

        item = {
            "PK": f"AUTHOR#{author_name}",
            "SK": "METADATA",
            "type": "AUTHOR",
            "Name": author_name,
            "Birthday": "2020-01-01"
        }

        TABLE_RESOURCE.put_item(Item=item)

        for b in range(num_books_per_author):
            book_name = f"book_{b} by author_{i}"
            book_isbn = f"978-{random.randint(1_000_000_000, 9_999_000_000)}"
        
            item = {
                "PK": f"AUTHOR#{author_name}",
                "SK": f"ISBN#{book_isbn}",
                "type": "BOOK",
                "Author": author_name,
                "Title": book_name,
                "GSI1PK": f"ISBN#{book_isbn}",
                "GSI1SK": f"ISBN#{book_isbn}"
            }

            TABLE_RESOURCE.put_item(Item=item)

def get_some_books():
    author = "author_1"
    books = [f"book_{i} by {author}" for i in range(5)]

    TABLE_RESOURCE

def get_author_by_name(author_name: str) -> dict:

    table = boto3.resource("dynamodb").Table(TABLE_NAME)

    response = table.get_item(
        Key={
            "PK": f"AUTHOR#{author_name}",
            "SK": "METADATA"
        }
    )

    return response["Item"]

def get_all_author_information(author_name: str) -> typing.List[dict]:

    table = boto3.resource("dynamodb").Table(TABLE_NAME)

    response = table.query(
        KeyConditionExpression=conditions.Key("PK").eq(f"AUTHOR#{author_name}")
    )

    return response["Items"]

def get_books_by_author(author_name: str) -> typing.List[dict]:

    table = boto3.resource("dynamodb").Table(TABLE_NAME)

    response = table.query(
        KeyConditionExpression=conditions.Key("PK").eq(f"AUTHOR#{author_name}") \
            & conditions.Key("SK").begins_with("ISBN")
    )

    return response["Items"]

def get_book_by_isbn(isbn: str) -> dict:

    table = boto3.resource("dynamodb").Table(TABLE_NAME)

    response = table.query(
        KeyConditionExpression=conditions.Key("GSI1PK").eq(f"ISBN#{isbn}") \
            & conditions.Key("GSI1SK").eq(f"ISBN#{isbn}"),
        IndexName="GSI1"
    )

    return response["Items"][0]

def create_table_with_sample_data():
    create_table()
    generate_sample_data()

if __name__ == "__main__":
    pass
    # create_table_with_sample_data()

    # print(get_author_by_name("author_1"))
    # print(get_all_author_information("author_1"))
    # print(get_books_by_author("author_1"))

    # print(get_book_by_isbn("978-1123541827"))
