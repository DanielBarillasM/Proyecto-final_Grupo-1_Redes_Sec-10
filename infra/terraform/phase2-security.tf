resource "aws_security_group" "visitas_client" {
  name        = "${var.phase2_project_name}-visitas-client-sg"
  description = "Cliente temporal de Visitas: Internet permitido, redes internas bloqueadas"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Administracion SSH unicamente desde el bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  ingress {
    description     = "Pruebas iniciadas desde TI"
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.ti.id]
  }

  egress {
    description = "DNS mediante el resolvedor de la VPC"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["10.10.0.2/32"]
  }

  egress {
    description = "DNS TCP mediante el resolvedor de la VPC"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["10.10.0.2/32"]
  }

  egress {
    description = "Navegacion HTTP a Internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Navegacion HTTPS a Internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-visitas-client-sg"
    Segment = "visitas"
  })
}

resource "aws_security_group" "ti" {
  name        = "${var.phase2_project_name}-ti-sg"
  description = "TI puede iniciar pruebas hacia todos los segmentos; no recibe conexiones laterales"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Administracion SSH unicamente desde el bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress {
    description = "Pruebas iniciadas por TI hacia la VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-ti-sg"
    Segment = "ti"
  })
}

resource "aws_security_group" "dns" {
  name        = "${var.phase2_project_name}-dns-sg"
  description = "DNS interno accesible solo desde segmentos autorizados"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Consultas DNS UDP internas"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [
      local.subnets.ventas.cidr,
      local.subnets.ti.cidr,
      local.subnets.datacenter.cidr,
      local.subnets.administracion.cidr,
    ]
  }

  ingress {
    description = "Consultas DNS TCP internas"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = [
      local.subnets.ventas.cidr,
      local.subnets.ti.cidr,
      local.subnets.datacenter.cidr,
      local.subnets.administracion.cidr,
    ]
  }

  ingress {
    description     = "Administracion SSH unicamente desde el bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress {
    description = "Comunicacion interna controlada"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-dns-sg"
    Segment = "datacenter"
  })
}

resource "aws_security_group" "intranet" {
  name        = "${var.phase2_project_name}-intranet-sg"
  description = "Intranet RRHH accesible desde redes internas excepto Visitas"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP desde segmentos internos autorizados"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [
      local.subnets.ventas.cidr,
      local.subnets.ti.cidr,
      local.subnets.datacenter.cidr,
      local.subnets.administracion.cidr,
    ]
  }

  ingress {
    description     = "Administracion SSH unicamente desde el bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress {
    description = "Comunicacion interna controlada"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-intranet-sg"
    Segment = "datacenter"
  })
}

resource "aws_security_group" "public_web" {
  name        = "${var.phase2_project_name}-public-web-sg"
  description = "Web publica de Ventas en la DMZ"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP publico"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  dynamic "ingress" {
    for_each = var.enable_https ? [1] : []

    content {
      description = "HTTPS publico"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  ingress {
    description     = "Administracion SSH unicamente desde el bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress {
    description = "DNS mediante el resolvedor de la VPC"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["10.10.0.2/32"]
  }

  egress {
    description = "DNS TCP mediante el resolvedor de la VPC"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["10.10.0.2/32"]
  }

  egress {
    description = "HTTP saliente para actualizaciones y validaciones"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "HTTPS saliente para actualizaciones y ACME"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-public-web-sg"
    Segment = "dmz"
  })
}
