
# Complexity costs: Read performance for nested DynamoDB items with different Lambda configurations

This is the companion repo to my (soon to be published) blog post about the influence of the Lambda memory size on how long it takes to read items from DynamoDB of different sizes and in different formats.

## Architecture

This CDK app deploys the infrastructure to measure how long it takes to read items from DynamoDB in different formats and memory configurations using the boto3 resource and client APIs.

To do that, we have an invocation mechanism that consists of a Lambda function that sends `n` messages to an SNS topic.
It also creates some sample items in the experiment table, that are later read by the other Lambdas.
This SNS topic is then used to trigger a set of Lambda functions with different memory configurations that take the measurements and record the results in a DynamoDB table.
Lastly there is a Lambda function to fetch the results from DynamoDB and aggregate them into a little CSV file.

![Architecture diagram](architecture.png)

## Try it yourself

### Prerequisites

- The CDK in version >= 1.90.0, install via `npm install -g aws-cdk`
- Python in version >= 3.7
- An AWS Account :-)

### Setup

1. Clone the repo and navigate to this directory
2. Run `python -m venv .venv` to create a virtual environment (`python3` on Mac/Linux)
3. Activate the virtual environment by calling `source .venv\bin\activate`
4. Install the dependencies using `pip install -r requirements.txt`
5. Run `cdk synth` to verify everything is set up correctly
6. Deploy the architecture to AWS with the CDK: `cdk deploy`, approve the creation of IAM resources.

### Run it yourself

The output of `cdk deploy` shows two functions which you're going to need:

```text
Outputs:
cdk-dynamodb-large-items.invokerFn = cdk-python-lambda-init-experimentinvokerfunctionB6-17SC5JUNTOAL4
cdk-dynamodb-large-items.resultAggregatorFn = cdk-python-lambda-init-resultaggregator1ED9DB61-1F0I2CYMTM6NM
```

The `invokerFn` is used to start the measurements.
You can send it an empty event or one that looks like this:

```json
{
    "n": 100
}
```

Where 100 is the amount of samples you want to collect. Once you invoke the function, it will start the measurements.
Note that this starts these measurements with a delay of a couple of seconds, because we might get throttled if we ramp up too fast even with On-Demand capacity.

You can then use the `resultAggregatorFn` to collect the results from the table and aggregate them as the name suggests.

Run the function with any event, it doesn't matter. In the logs you'll find a csv-formatted table with the measurements, which you can then import into something like Excel to make pretty graphs.

### Customization

To customize the amount of functions that get created as well as the increments and min and max memory, edit these variables in `infrastructure/cdk_python_lambda_init_stack.py`:

```python
LAMBDA_MEMORY_MIN_SIZE_IN_MB = 128
LAMBDA_MEMORY_INCREMENTS_IN_MB = 128
LAMBDA_MEMORY_MAX_SIZE_IN_MB = 2048
```

(Don't forget to do a `cdk deploy` afterwards.)

Have fun!

### Teardown

Run `cdk destroy` to remove the infrastructure. The Lambda log groups will remain, I couldn't figure out how to set the removal policies on those in an easy way - the rest should be completely deleted ;-)

## Result

The results are also available as [result.csv](result.csv) in the repo.

![](boto3_dynamodb_client.png)

![](boto3_dynamodb_resource.png)

|memorySize|4KB_FLAT_C|4KB_FLAT_R|4KB_NESTED_C|4KB_NESTED_R|64KB_FLAT_C|64KB_FLAT_R|64KB_NESTED_C|64KB_NESTED_R|128KB_FLAT_C|128KB_FLAT_R|128KB_NESTED_C|128KB_NESTED_R|256KB_FLAT_C|256KB_FLAT_R|256KB_NESTED_C|256KB_NESTED_R|400KB_FLAT_C|400KB_FLAT_R|400KB_NESTED_C|400KB_NESTED_R|DESERIALIZE_FLAT|DESERIALIZE_NESTED|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|128|34|39|88|102|53|58|728|931|58|60|1442|1663|94|76|2882|3536|133|104|4539|5474|7|494|
|256|15|18|36|42|24|24|359|445|29|30|712|847|41|36|1439|1734|60|47|2280|2782|1|230|
|384|8|8|21|22|11|13|234|286|16|17|475|564|25|21|962|1160|33|28|1530|1844|0|138|
|512|6|7|11|14|8|8|170|210|12|12|347|425|18|17|713|872|25|22|1129|1394|0|103|
|640|5|5|9|11|7|8|133|169|10|11|280|338|17|15|574|700|23|21|910|1120|0|76|
|768|5|5|9|9|8|8|117|138|11|10|240|280|17|14|492|581|22|19|777|931|0|60|
|896|5|5|9|9|7|7|103|122|10|10|206|244|15|14|426|506|22|19|673|808|0|49|
|1024|5|5|9|9|7|7|91|108|10|11|182|216|15|15|375|444|20|19|592|711|0|43|
|1152|5|5|9|9|7|7|83|100|10|9|167|198|14|13|338|403|20|18|534|637|0|41|
|1280|5|5|9|9|7|7|77|92|11|10|155|181|14|14|312|368|20|18|490|582|0|36|
|1408|5|5|9|9|8|7|71|85|10|10|141|166|14|13|284|339|20|17|447|537|0|31|
|1536|5|5|9|9|7|7|69|82|10|10|133|159|14|12|264|317|20|17|416|499|0|32|
|1664|5|5|8|9|7|7|67|79|10|10|129|152|14|12|255|304|20|17|403|481|0|29|
|1792|5|5|9|9|7|7|65|76|10|10|122|144|14|13|236|280|20|18|367|441|0|27|
|1920|5|5|9|9|7|7|65|76|11|10|123|145|14|12|237|283|20|18|372|443|0|28|
|2048|5|5|8|9|7|7|64|76|10|10|122|143|14|13|234|279|20|18|365|439|0|28|
