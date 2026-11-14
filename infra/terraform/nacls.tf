# Las NACL son stateless. Las reglas de retorno se declaran de forma explícita y
# se complementan con Security Groups stateful en las instancias.

resource "aws_network_acl" "visitas" {
  vpc_id = aws_vpc.main.id

  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = local.subnets.administracion.cidr
    from_port  = 22
    to_port    = 22
  }

  ingress {
    protocol   = "-1"
    rule_no    = 110
    action     = "allow"
    cidr_block = local.subnets.ti.cidr
    from_port  = 0
    to_port    = 0
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 120
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
    to_port    = 65535
  }

  ingress {
    protocol   = "udp"
    rule_no    = 130
    action     = "allow"
    cidr_block = "10.10.0.2/32"
    from_port  = 1024
    to_port    = 65535
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 140
    action     = "allow"
    cidr_block = "10.10.0.2/32"
    from_port  = 1024
    to_port    = 65535
  }

  egress {
    protocol   = "udp"
    rule_no    = 80
    action     = "allow"
    cidr_block = "10.10.0.2/32"
    from_port  = 53
    to_port    = 53
  }

  egress {
    protocol   = "tcp"
    rule_no    = 81
    action     = "allow"
    cidr_block = "10.10.0.2/32"
    from_port  = 53
    to_port    = 53
  }

  egress {
    protocol   = "tcp"
    rule_no    = 90
    action     = "allow"
    cidr_block = local.subnets.ti.cidr
    from_port  = 1024
    to_port    = 65535
  }

  egress {
    protocol   = "udp"
    rule_no    = 91
    action     = "allow"
    cidr_block = local.subnets.ti.cidr
    from_port  = 1024
    to_port    = 65535
  }

  egress {
    protocol   = "tcp"
    rule_no    = 92
    action     = "allow"
    cidr_block = local.subnets.administracion.cidr
    from_port  = 1024
    to_port    = 65535
  }

  egress {
    protocol   = "-1"
    rule_no    = 100
    action     = "deny"
    cidr_block = var.vpc_cidr
    from_port  = 0
    to_port    = 0
  }

  egress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 80
    to_port    = 80
  }

  egress {
    protocol   = "tcp"
    rule_no    = 120
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 443
    to_port    = 443
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-visitas-nacl"
    Segment = "visitas"
  })
}

resource "aws_network_acl_association" "visitas" {
  network_acl_id = aws_network_acl.visitas.id
  subnet_id      = aws_subnet.segments["visitas"].id
}

resource "aws_network_acl" "ti" {
  vpc_id = aws_vpc.main.id

  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = local.subnets.administracion.cidr
    from_port  = 22
    to_port    = 22
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = var.vpc_cidr
    from_port  = 1024
    to_port    = 65535
  }

  ingress {
    protocol   = "udp"
    rule_no    = 120
    action     = "allow"
    cidr_block = var.vpc_cidr
    from_port  = 1024
    to_port    = 65535
  }

  ingress {
    protocol   = "-1"
    rule_no    = 200
    action     = "deny"
    cidr_block = var.vpc_cidr
    from_port  = 0
    to_port    = 0
  }

  egress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = var.vpc_cidr
    from_port  = 0
    to_port    = 0
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-ti-nacl"
    Segment = "ti"
  })
}

resource "aws_network_acl_association" "ti" {
  network_acl_id = aws_network_acl.ti.id
  subnet_id      = aws_subnet.segments["ti"].id
}

resource "aws_network_acl" "dmz" {
  vpc_id = aws_vpc.main.id

  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 80
    to_port    = 80
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 443
    to_port    = 443
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 120
    action     = "allow"
    cidr_block = local.subnets.administracion.cidr
    from_port  = 22
    to_port    = 22
  }

  ingress {
    protocol   = "-1"
    rule_no    = 130
    action     = "allow"
    cidr_block = local.subnets.ti.cidr
    from_port  = 0
    to_port    = 0
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 140
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
    to_port    = 65535
  }

  ingress {
    protocol   = "udp"
    rule_no    = 150
    action     = "allow"
    cidr_block = "10.10.0.2/32"
    from_port  = 1024
    to_port    = 65535
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 160
    action     = "allow"
    cidr_block = "10.10.0.2/32"
    from_port  = 1024
    to_port    = 65535
  }

  egress {
    protocol   = "udp"
    rule_no    = 80
    action     = "allow"
    cidr_block = "10.10.0.2/32"
    from_port  = 53
    to_port    = 53
  }

  egress {
    protocol   = "tcp"
    rule_no    = 81
    action     = "allow"
    cidr_block = "10.10.0.2/32"
    from_port  = 53
    to_port    = 53
  }

  egress {
    protocol   = "tcp"
    rule_no    = 90
    action     = "allow"
    cidr_block = local.subnets.administracion.cidr
    from_port  = 1024
    to_port    = 65535
  }

  egress {
    protocol   = "tcp"
    rule_no    = 91
    action     = "allow"
    cidr_block = local.subnets.ti.cidr
    from_port  = 1024
    to_port    = 65535
  }

  egress {
    protocol   = "udp"
    rule_no    = 92
    action     = "allow"
    cidr_block = local.subnets.ti.cidr
    from_port  = 1024
    to_port    = 65535
  }

  egress {
    protocol   = "-1"
    rule_no    = 100
    action     = "deny"
    cidr_block = var.vpc_cidr
    from_port  = 0
    to_port    = 0
  }

  egress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
    to_port    = 65535
  }

  egress {
    protocol   = "tcp"
    rule_no    = 120
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 80
    to_port    = 80
  }

  egress {
    protocol   = "tcp"
    rule_no    = 130
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 443
    to_port    = 443
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-dmz-nacl"
    Segment = "dmz"
  })
}

resource "aws_network_acl_association" "dmz" {
  network_acl_id = aws_network_acl.dmz.id
  subnet_id      = aws_subnet.segments["dmz"].id
}
