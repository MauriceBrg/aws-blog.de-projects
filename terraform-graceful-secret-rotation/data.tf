data "aws_caller_identity" "this" {

}

data "aws_iam_policy" "lambda-basic-execution" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
