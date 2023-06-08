resource "aws_secretsmanager_secret" "reader-credentials" {
  name = "${var.iam-user-name}-credentials"

}

resource "aws_secretsmanager_secret_rotation" "reader-credentials-rotation" {

  secret_id           = aws_secretsmanager_secret.reader-credentials.id
  rotation_lambda_arn = aws_lambda_function.credential-updater.arn

  rotation_rules {
    automatically_after_days = var.rotate-credentials-every-n-days
    duration                 = "2h"
  }

}
