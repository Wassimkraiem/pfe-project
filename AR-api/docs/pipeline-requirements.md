# Pipeline requirements (infra outputs and Bitbucket vars)

This repo’s CI/CD does **not** run Terraform. It only needs **outputs from your infra project** (or equivalent values) as **Bitbucket repository variables** so it can:

1. Build the app image and push it to ECR.
2. Update App Runner service(s) to use the new image.

---

## What the infra project must provide

Use these as Terraform **outputs** in your staging infra, then copy their values into Bitbucket repo variables.

| Output name (suggestion) | Description | Bitbucket variable |
|--------------------------|-------------|---------------------|
| `ecr_repository_url` | Full ECR URL, e.g. `123456789012.dkr.ecr.us-east-1.amazonaws.com/authentic-rights-api-staging` | `ECR_REPOSITORY_URL` |
| `apprunner_web_service_arn` | ARN of the App Runner service for the web API | `APP_RUNNER_WEB_SERVICE_ARN` |
| `apprunner_worker_service_arn` | (Optional) ARN of the App Runner service for the Celery worker | `APP_RUNNER_WORKER_SERVICE_ARN` |
| `bitbucket_oidc_role_arn` | IAM role ARN that Bitbucket OIDC can assume for this repo | `AWS_OIDC_ROLE_ARN` |

Infra must also:

- **ECR**: One private ECR repository. App Runner and the pipeline will use the same repo; the pipeline pushes tag `staging-latest` (or the value of `IMAGE_TAG`).
- **App Runner**: Service(s) created with **source = ECR image** (not GitHub/CodeCommit). The image identifier in Terraform can use a variable, e.g. `image_tag = "staging-latest"`, so the first deploy works; later deploys are done by the pipeline via `aws apprunner update-service` with the same tag.
- **OIDC**: Configure Bitbucket as an OIDC IdP in IAM and create a role that:
  - Is assumed via the Bitbucket OIDC provider (audience and repo filters as needed).
  - Has a policy allowing:
    - `ecr:GetAuthorizationToken` (account).
    - On the ECR repo: `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, `ecr:BatchCheckLayerAvailability`, `ecr:PutImage`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`.
    - `apprunner:UpdateService`, `apprunner:DescribeService`, `apprunner:DescribeServiceUpdate` (and optionally list) so the pipeline can update the service(s) and wait if needed.

---

## Bitbucket repository variables

Set these in **Repository settings → Pipelines → Repository variables**. Mark as **Secured** any that are secret (e.g. if you ever store a token; the ones below are ARNs/URLs and usually non-secret).

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_OIDC_ROLE_ARN` | Yes | IAM role ARN for OIDC (from infra output `bitbucket_oidc_role_arn`). |
| `ECR_REPOSITORY_URL` | Yes | Full ECR URL (from infra output `ecr_repository_url`). |
| `APP_RUNNER_WEB_SERVICE_ARN` | At least one | App Runner web service ARN (from infra `apprunner_web_service_arn`). |
| `APP_RUNNER_WORKER_SERVICE_ARN` | No | App Runner worker service ARN if you run the worker on App Runner. |
| `AWS_REGION` | No | AWS region (default `us-east-1`). |
| `APP_SOURCE_DIR` | No | Directory containing `Dockerfile` (default `.`). |
| `IMAGE_TAG` | No | Tag to push and deploy (default `staging-latest`). |

Pipeline runs on **push to `staging`**. It will fail fast if `AWS_OIDC_ROLE_ARN`, `ECR_REPOSITORY_URL`, or `Dockerfile` is missing.

---

## One-time setup checklist

1. In the **infra** repo: create ECR repo, App Runner service(s) (image from that ECR, e.g. `staging-latest`), and Bitbucket OIDC role with the permissions above; output the four values.
2. In **Bitbucket**: enable Pipelines, add OIDC in the repo (or workspace), set the repository variables from the infra outputs.
3. Push to `staging`: pipeline builds, pushes image, then runs `aws apprunner update-service` so App Runner uses the new image.
