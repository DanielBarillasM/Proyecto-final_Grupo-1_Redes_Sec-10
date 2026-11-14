# =============================================================================
# Servicios de Data Center: DNS interno (BIND9) e intranet de RR. HH. (Nginx)
# Responsable: Andrés Rafael Chivalán
#
# Las configuraciones viven en services/dns/ y services/intranet/; Terraform
# las incrusta en base64 dentro del user_data para que la instancia no dependa
# de Git ni de Internet. Solo se crean con enable_phase2_compute = true.
# =============================================================================

locals {
  services_dir = "${path.module}/../../services"

  # Los archivos de zona y named.conf contienen estas IP de forma literal.
  datacenter_expected_ips = {
    dns      = "10.10.0.164"
    intranet = "10.10.0.165"
  }

  dns_user_data = templatefile("${path.module}/templates/dns-user-data.tftpl", {
    internal_domain  = var.internal_domain
    dns_ip           = local.phase2_service_ips.dns
    named_conf_b64   = filebase64("${local.services_dir}/dns/named.conf")
    zone_forward_b64 = filebase64("${local.services_dir}/dns/db.rednova.internal")
    zone_reverse_b64 = filebase64("${local.services_dir}/dns/db.10.10.0")
  })

  intranet_user_data = templatefile("${path.module}/templates/intranet-user-data.tftpl", {
    internal_domain = var.internal_domain
    dns_ip          = local.phase2_service_ips.dns
    intranet_ip     = local.phase2_service_ips.intranet
    index_html_b64  = filebase64("${local.services_dir}/intranet/index.html")
    nginx_conf_b64  = filebase64("${local.services_dir}/intranet/nginx.conf")
  })
}

resource "aws_instance" "dns" {
  count = var.enable_phase2_compute ? 1 : 0

  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.phase2_instance_type
  subnet_id                   = aws_subnet.segments["datacenter"].id
  private_ip                  = local.phase2_service_ips.dns
  vpc_security_group_ids      = [aws_security_group.dns.id]
  key_name                    = try(aws_key_pair.lab[0].key_name, null)
  associate_public_ip_address = false
  user_data                   = local.dns_user_data
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

  # El endpoint S3 debe existir antes del arranque para que dnf funcione.
  depends_on = [aws_vpc_endpoint.s3]

  lifecycle {
    precondition {
      condition     = var.enable_compute
      error_message = "enable_phase2_compute requiere enable_compute = true (llave SSH y bastión de Fase 1)."
    }
    precondition {
      condition     = local.phase2_service_ips.dns == local.datacenter_expected_ips.dns
      error_message = "La IP del DNS cambió: actualice services/dns/named.conf y las zonas antes de aplicar."
    }
    precondition {
      condition     = var.internal_domain == "rednova.internal"
      error_message = "internal_domain cambió: actualice los archivos de zona en services/dns/."
    }
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-dns"
    Role    = "dns-interno"
    Segment = "datacenter"
    Owner   = "andres"
  })
}

resource "aws_instance" "intranet" {
  count = var.enable_phase2_compute ? 1 : 0

  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.phase2_instance_type
  subnet_id                   = aws_subnet.segments["datacenter"].id
  private_ip                  = local.phase2_service_ips.intranet
  vpc_security_group_ids      = [aws_security_group.intranet.id]
  key_name                    = try(aws_key_pair.lab[0].key_name, null)
  associate_public_ip_address = false
  user_data                   = local.intranet_user_data
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

  depends_on = [aws_vpc_endpoint.s3, aws_instance.dns]

  lifecycle {
    precondition {
      condition     = var.enable_compute
      error_message = "enable_phase2_compute requiere enable_compute = true (llave SSH y bastión de Fase 1)."
    }
    precondition {
      condition     = local.phase2_service_ips.intranet == local.datacenter_expected_ips.intranet
      error_message = "La IP de la intranet cambió: actualice services/intranet/nginx.conf y la zona DNS."
    }
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-intranet-rrhh"
    Role    = "intranet-rrhh"
    Segment = "datacenter"
    Owner   = "andres"
  })
}
