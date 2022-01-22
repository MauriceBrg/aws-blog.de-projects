import boto3


def make_partitions_inherit_datatypes_of_table(database_name, table_name):
    glue_client = boto3.client("glue")
    
    # Get the data types of the base table
    table_response = glue_client.get_table(
        DatabaseName=database_name,
        Name=table_name
    )
    
    column_to_datatype = {
        item["Name"]: item["Type"] for item in table_response["Table"]["StorageDescriptor"]["Columns"]
    }
    
    # List partitions and datatypes
    
    partition_params = {
        "DatabaseName": database_name,
        "TableName": table_name,
    }
    response = glue_client.get_partitions(**partition_params)
    partitions = response["Partitions"]
    
    while "NextToken" in response:
        partition_params["NextToken"] = response["NextToken"]
        response = glue_client.get_partitions(**partition_params)
        
        partitions += response["Partitions"]
    
    print("Got", len(partitions), "partitions")
    
    partitions_to_update = []
    for partition in partitions:
        changed = False
        
        columns = partition["StorageDescriptor"]["Columns"]
        new_columns = []
        for column in columns:
            if column["Name"] in column_to_datatype and column["Type"] != column_to_datatype[column["Name"]]:
                changed = True
                
                # print(f"Changing type of {column['Name']} from {column['Type']} to {column_to_datatype[column['Name']]}")
                column["Type"] = column_to_datatype[column["Name"]]
            new_columns.append(column)
        
        partition["StorageDescriptor"]["Columns"] = new_columns
        
        if changed:
            partitions_to_update.append(partition)

    print(f"{len(partitions_to_update)} partitions of table {table_name} will be updated.")
    
    # Update partitions if necessary
    for partition in partitions_to_update:

        print(f"Updating {', '.join(partition['Values'])}")
        
        partition.pop("CatalogId")
        partition.pop("CreationTime")
        
        glue_client.update_partition(
            DatabaseName=partition.pop("DatabaseName"),
            TableName=partition.pop("TableName"),
            PartitionValueList=partition['Values'],
            PartitionInput=partition
        )

def main():

    database_name = "datalake"
    table_name = "products_partitioned"

    make_partitions_inherit_datatypes_of_table(
        database_name=database_name,
        table_name=table_name
    )

if __name__ == "__main__":
    main()
