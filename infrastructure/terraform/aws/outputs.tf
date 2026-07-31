output "instance_id" {
  value = aws_instance.platform.id
}

output "public_ip" {
  value = var.assign_elastic_ip ? aws_eip.platform[0].public_ip : aws_instance.platform.public_ip
}

output "elastic_ip" {
  value = var.assign_elastic_ip ? aws_eip.platform[0].public_ip : ""
}

output "private_ip" {
  value = aws_instance.platform.private_ip
}

output "region" {
  value = var.aws_region
}

output "ssh_username" {
  value = "ubuntu"
}

output "security_group_id" {
  value = aws_security_group.platform.id
}
