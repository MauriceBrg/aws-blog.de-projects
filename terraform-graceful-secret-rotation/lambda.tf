data "archive_file" "credential-updater-zip" {
  type             = "zip"
  source_file      = "${path.module}/credential_updater.py"
  output_path      = "credential_updater.zip"
  output_file_mode = "0666"
}

resource "aws_lambda_function" "credential-updater" {

  function_name = "CredentialUpdater-${var.iam-user-name}"
  runtime       = "python3.10"
  timeout       = 20
  memory_size   = 256

  role = aws_iam_role.role-for-credential-updater.arn

  filename         = data.archive_file.credential-updater-zip.output_path
  source_code_hash = data.archive_file.credential-updater-zip.output_base64sha256

  handler = "credential_updater.lambda_handler"

  environment {
    variables = {
      "IAM_USERNAME" : aws_iam_user.reader.name,
      "DELETE_OLD_AFTER_N_MINUTES" : tostring(var.credential-grace-period-in-minutes),
      "SCHEDULER_ROLE_ARN" : aws_iam_role.role-for-secret-deletion-scheduler.arn,
    }
  }

}

resource "aws_lambda_permission" "from-credential-rotation" {

  statement_id  = "AllowFromSecretsmanager"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.credential-updater.function_name

  principal  = "secretsmanager.amazonaws.com"
  source_arn = aws_secretsmanager_secret.reader-credentials.arn

}
