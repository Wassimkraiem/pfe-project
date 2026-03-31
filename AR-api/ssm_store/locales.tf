locals {
  ssm_name_arn_map = zipmap(
    data.aws_ssm_parameters_by_path.main.names,
    data.aws_ssm_parameters_by_path.main.arns
  )
}



data "aws_ssm_parameters_by_path" "main" {
  path            = "/bviral/authentic_rights_api/${var.ENV}/"
  recursive       = false
  with_decryption = true
}
