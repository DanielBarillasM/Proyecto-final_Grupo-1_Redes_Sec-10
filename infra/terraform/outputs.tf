output "vpc_id" {
  description = "Identificador de la VPC creada."
  value       = aws_vpc.main.id
}

output "subnet_ids" {
  description = "Identificadores y CIDR de las subredes."
  value = {
    for name, subnet in aws_subnet.segments : name => {
      id   = subnet.id
      cidr = subnet.cidr_block
    }
  }
}

output "bastion_public_ip" {
  description = "IP pública temporal del bastión, si se habilitó cómputo."
  value       = try(aws_instance.bastion[0].public_ip, null)
}

output "ventas_private_ips" {
  description = "IP privadas usadas en la prueba de ping."
  value       = aws_instance.ventas[*].private_ip
}
