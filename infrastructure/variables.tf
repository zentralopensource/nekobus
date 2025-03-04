variable "name" {
  default = "Nekobus"
}

variable "tags" {
  default = {}
  type    = map(string)
}

# Lambda archive

variable "zip_archive_s3_bucket" {
  description = "Name of the S3 bucket where the ZIP archive is hosted"
  type        = string
}

variable "zip_archive_s3_key" {
  description = "S3 key of the ZIP archive to deploy"
  type        = string
}

# Jamf

variable "jamf_base_url" {
  type = string
}

variable "jamf_client_id" {
  type = string
}

variable "jamf_client_secret" {
  type      = string
  sensitive = true
}

# Zentral

variable "zentral_base_url" {
  type = string
}

variable "zentral_token" {
  type      = string
  sensitive = true
}

variable "profile_uuid" {
  type = string
}

variable "taxonomy" {
  type = string
}

variable "ready_tag" {
  type = string
}

variable "started_tag" {
  type = string
}

variable "unenrolled_tag" {
  type = string
}

variable "finished_tag" {
  type = string
}
