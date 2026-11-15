# =============================================================================
# Clientes temporales de prueba: Visitas (10.10.0.4) y TI (10.10.0.132)
# Responsable: Genser Catalán
#
# Solo existen durante la ventana autorizada (enable_phase2_compute = true) y
# se retiran al cerrarla. No exponen servicios: el cliente de Visitas recibe una
# IPv4 pública efímera únicamente para demostrar salida a Internet; su Security
# Group no tiene ninguna regla de entrada desde Internet.
# =============================================================================

locals {
  test_client_expected_ips = {
    visitas = "10.10.0.4"
    ti      = "10.10.0.132"
  }

  test_client_common = {
    internal_domain = var.internal_domain
    dns_ip          = local.phase2_service_ips.dns
    hardening_b64   = filebase64("${local.services_dir}/hardening/hardening.sh")
    dnsquery_b64    = filebase64("${local.services_dir}/dns/dnsquery.py")
  }

  visitas_client_user_data = templatefile("${path.module}/templates/test-client-user-data.tftpl", merge(local.test_client_common, {
    role                   = "visitas"
    client_ip              = local.phase2_service_ips.visitas_client
    wait_for_internet      = true
    configure_internal_dns = false
  }))

  ti_client_user_data = templatefile("${path.module}/templates/test-client-user-data.tftpl", merge(local.test_client_common, {
    role                   = "ti"
    client_ip              = local.phase2_service_ips.ti_client
    wait_for_internet      = false
    configure_internal_dns = true
  }))
}

resource "aws_instance" "visitas_client" {
  count = var.enable_phase2_compute ? 1 : 0

  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.phase2_instance_type
  subnet_id              = aws_subnet.segments["visitas"].id
  private_ip             = local.phase2_service_ips.visitas_client
  vpc_security_group_ids = [aws_security_group.visitas_client.id]
  key_name               = try(aws_key_pair.lab[0].key_name, null)

  # Salida explícita y temporal: la subred no asigna IPv4 pública por defecto.
  # La IPv4 desaparece al destruir la instancia (no es una Elastic IP).
  associate_public_ip_address = true
  user_data                   = local.visitas_client_user_data
  user_data_replace_on_change = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    encrypted   = true
    volume_size = 8
    volume_type = "gp3"
  }

  lifecycle {
    precondition {
      condition     = var.enable_compute
      error_message = "enable_phase2_compute requiere enable_compute = true (llave SSH y bastión de Fase 1)."
    }
    precondition {
      condition     = local.phase2_service_ips.visitas_client == local.test_client_expected_ips.visitas
      error_message = "La IP del cliente de Visitas cambió: actualice scripts/test-phase2.ps1 y scripts/validate-phase2.py."
    }
  }

  tags = merge(local.phase2_tags, {
    Name      = "${var.phase2_project_name}-cliente-visitas"
    Role      = "cliente-pruebas-visitas"
    Segment   = "visitas"
    Owner     = "genser"
    Temporary = "true"
  })
}

resource "aws_instance" "ti_client" {
  count = var.enable_phase2_compute ? 1 : 0

  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.phase2_instance_type
  subnet_id                   = aws_subnet.segments["ti"].id
  private_ip                  = local.phase2_service_ips.ti_client
  vpc_security_group_ids      = [aws_security_group.ti.id]
  key_name                    = try(aws_key_pair.lab[0].key_name, null)
  associate_public_ip_address = false
  user_data                   = local.ti_client_user_data
  user_data_replace_on_change = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    encrypted   = true
    volume_size = 8
    volume_type = "gp3"
  }

  # TI resuelve *.rednova.internal con BIND9; conviene que el DNS exista primero.
  depends_on = [aws_instance.dns]

  lifecycle {
    precondition {
      condition     = var.enable_compute
      error_message = "enable_phase2_compute requiere enable_compute = true (llave SSH y bastión de Fase 1)."
    }
    precondition {
      condition     = local.phase2_service_ips.ti_client == local.test_client_expected_ips.ti
      error_message = "La IP del cliente de TI cambió: actualice services/dns/db.rednova.internal y los scripts de prueba."
    }
  }

  tags = merge(local.phase2_tags, {
    Name      = "${var.phase2_project_name}-cliente-ti"
    Role      = "cliente-pruebas-ti"
    Segment   = "ti"
    Owner     = "genser"
    Temporary = "true"
  })
}

output "test_clients" {
  description = "Clientes temporales de prueba y bastión usado como salto (null mientras el cómputo de Fase 2 esté deshabilitado)."
  value = {
    visitas = {
      instance_id = try(aws_instance.visitas_client[0].id, null)
      private_ip  = try(aws_instance.visitas_client[0].private_ip, null)
      public_ip   = try(aws_instance.visitas_client[0].public_ip, null)
    }
    ti = {
      instance_id = try(aws_instance.ti_client[0].id, null)
      private_ip  = try(aws_instance.ti_client[0].private_ip, null)
    }
    bastion_private_ip = try(aws_instance.bastion[0].private_ip, null)
  }
}
