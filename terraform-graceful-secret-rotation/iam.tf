
resource "aws_iam_user" "reader" {
  name = var.iam-user-name
}


// Policy that the credential updater lambda can use to create/update/delete credentials.
data "aws_iam_policy_document" "credential-updater" {

  statement {
    sid = "ManageCredentialsForReader"
    actions = [
      "iam:CreateAccessKey",
      "iam:DeleteAccessKey",
    ]
    resources = [
      aws_iam_user.reader.arn
    ]
  }

  statement {
    sid = "ReadWriteSecret"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
      "secretsmanager:PutSecretValue",
      "secretsmanager:UpdateSecretVersionStage",
    ]
    resources = [
      aws_secretsmanager_secret.reader-credentials.arn
    ]
  }

  statement {
    sid = "CreateDeletionSchedule"
    actions = [
      "scheduler:CreateSchedule",
      "scheduler:DeleteSchedule",
    ]
    resources = [
      "arn:aws:scheduler:*:*:schedule/*/DeletePreviousAK*"
    ]
  }

  statement {
    sid = "CreateDeletionSchedulePassRole"
    actions = [
      "iam:PassRole",
    ]
    resources = [
      aws_iam_role.role-for-secret-deletion-scheduler.arn
    ]
  }
}

resource "aws_iam_policy" "credential-updater-policy" {
  policy = data.aws_iam_policy_document.credential-updater.json
}

data "aws_iam_policy_document" "assume-role-credential-updater" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "role-for-credential-updater" {
  name_prefix        = "CredentialUpdater"
  assume_role_policy = data.aws_iam_policy_document.assume-role-credential-updater.json
}

resource "aws_iam_role_policy_attachment" "credential-updater" {
  role       = aws_iam_role.role-for-credential-updater.name
  policy_arn = aws_iam_policy.credential-updater-policy.arn
}

resource "aws_iam_role_policy_attachment" "credential-updater-basic" {
  role       = aws_iam_role.role-for-credential-updater.name
  policy_arn = data.aws_iam_policy.lambda-basic-execution.arn
}

data "aws_iam_policy_document" "assume-role-secret-deletion-scheduler" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "execute-credential-updater-policy" {
  statement {

    actions = ["lambda:InvokeFunction"]

    resources = [
      aws_lambda_function.credential-updater.arn
    ]
  }
}

resource "aws_iam_policy" "execute-credential-updater-policy" {
  policy = data.aws_iam_policy_document.execute-credential-updater-policy.json
}

resource "aws_iam_role" "role-for-secret-deletion-scheduler" {
  name_prefix        = "SecretDeletionScheduler"
  assume_role_policy = data.aws_iam_policy_document.assume-role-secret-deletion-scheduler.json
}

resource "aws_iam_role_policy_attachment" "execute-credential-updater-basic" {
  role       = aws_iam_role.role-for-secret-deletion-scheduler.name
  policy_arn = aws_iam_policy.execute-credential-updater-policy.arn
}


