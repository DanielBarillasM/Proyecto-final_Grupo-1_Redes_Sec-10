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

output "dmz_subnet" {
  description = "Identificador y CIDR de la DMZ de Fase 2."
  value = {
    id   = aws_subnet.segments["dmz"].id
    cidr = aws_subnet.segments["dmz"].cidr_block
  }
}

output "dmz_route_table_id" {
  description = "Tabla de rutas pública dedicada a la DMZ."
  value       = aws_route_table.dmz_public.id
}

output "phase2_reserved_cidr" {
  description = "Bloque conservado para crecimiento después de separar la DMZ."
  value       = local.phase2_reserved_cidr
}

output "phase2_service_ips" {
  description = "Direcciones privadas propuestas para servicios y clientes de Fase 2."
  value       = local.phase2_service_ips
}

output "phase2_domains" {
  description = "Dominios configurados para los servicios internos y públicos."
  value = {
    internal = var.internal_domain
    rrhh     = "rrhh.${var.internal_domain}"
    public   = var.public_domain
    https    = var.enable_https
  }
}

output "phase2_network_acl_ids" {
  description = "NACL administradas para Visitas, TI y DMZ."
  value = {
    visitas = aws_network_acl.visitas.id
    ti      = aws_network_acl.ti.id
    dmz     = aws_network_acl.dmz.id
  }
}

output "phase2_compute_enabled" {
  description = "Indica si el cómputo de Fase 2 fue habilitado explícitamente."
  value       = var.enable_phase2_compute
}

output "datacenter_services" {
  description = "DNS interno e intranet de RR. HH. en Data Center (null si el cómputo de Fase 2 está deshabilitado)."
  value = {
    dns = {
      instance_id = try(aws_instance.dns[0].id, null)
      private_ip  = try(aws_instance.dns[0].private_ip, null)
      fqdn        = "ns1.${var.internal_domain}"
    }
    intranet = {
      instance_id = try(aws_instance.intranet[0].id, null)
      private_ip  = try(aws_instance.intranet[0].private_ip, null)
      fqdn        = "rrhh.${var.internal_domain}"
      url         = "http://rrhh.${var.internal_domain}/"
    }
    s3_gateway_endpoint = try(aws_vpc_endpoint.s3[0].id, null)
  }
}
