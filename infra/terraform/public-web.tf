locals {
  public_web_expected_ip = "10.10.0.196"

  public_web_user_data = templatefile("${path.module}/templates/public-web-user-data.tftpl", {
    public_domain  = var.public_domain
    enable_https   = var.enable_https
    internal_ip    = local.phase2_service_ips.public_web
    index_html_b64 = filebase64("${local.services_dir}/public-web/index.html")
    nginx_conf_b64 = filebase64("${local.services_dir}/public-web/nginx.conf")
    hardening_b64  = filebase64("${local.services_dir}/hardening/hardening.sh")
  })
}

resource "aws_instance" "public_web" {
  count = var.enable_phase2_compute ? 1 : 0

  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.phase2_instance_type
  subnet_id              = aws_subnet.segments["dmz"].id
  private_ip             = local.phase2_service_ips.public_web
  vpc_security_group_ids = [aws_security_group.public_web.id]
  key_name               = try(aws_key_pair.lab[0].key_name, null)

  # Sin IPv4 automática: la única IPv4 pública es la Elastic IP explícita de abajo.
  # El user_data espera a que la EIP quede asociada antes de usar dnf.
  associate_public_ip_address = false
  user_data                   = local.public_web_user_data
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
      condition     = local.phase2_service_ips.public_web == local.public_web_expected_ip
      error_message = "La IP de la web pública cambió: actualice services/public-web/nginx.conf, la zona web-dmz y las pruebas."
    }
    precondition {
      condition     = !var.enable_https || var.public_domain != ""
      error_message = "enable_https = true requiere public_domain (el certificado se emite para ese nombre)."
    }
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-public-web"
    Role    = "web-publica-ventas"
    Segment = "dmz"
    Owner   = "roberto"
  })
}

# IPv4 pública estable durante las pruebas. Es temporal: se libera con terraform
# destroy (o al poner enable_phase2_compute = false) al cerrar la ventana.
resource "aws_eip" "public_web" {
  count = var.enable_phase2_compute ? 1 : 0

  domain   = "vpc"
  instance = aws_instance.public_web[0].id

  depends_on = [aws_internet_gateway.main]

  tags = merge(local.phase2_tags, {
    Name      = "${var.phase2_project_name}-public-web-eip"
    Role      = "web-publica-ventas"
    Segment   = "dmz"
    Owner     = "roberto"
    Temporary = "true"
  })
}

output "public_web" {
  description = "Web pública de Ventas en la DMZ (null mientras el cómputo de Fase 2 esté deshabilitado)."
  value = {
    instance_id = try(aws_instance.public_web[0].id, null)
    private_ip  = try(aws_instance.public_web[0].private_ip, null)
    public_ip   = try(aws_eip.public_web[0].public_ip, null)
    url_by_ip   = try("http://${aws_eip.public_web[0].public_ip}/", null)
    domain      = var.public_domain == "" ? null : var.public_domain
    url_domain  = var.public_domain == "" ? null : "${var.enable_https ? "https" : "http"}://${var.public_domain}/"
    https       = var.enable_https
  }
}

output "public_dns_record" {
  description = "Registro A que debe crearse en el DNS público (solo con autorización de Andrés). No se crea desde Terraform."
  value = (
    var.public_domain == "" ? "Defina public_domain para generar el registro." :
    try("${var.public_domain}  A  ${aws_eip.public_web[0].public_ip}  (TTL 300)", "${var.public_domain}  A  <Elastic IP del apply>  (TTL 300)")
  )
}
