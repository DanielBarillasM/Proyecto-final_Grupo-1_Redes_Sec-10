resource "aws_security_group" "bastion" {
  name        = "${var.project_name}-bastion-sg"
  description = "SSH de entrada limitado a la IP administrativa"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH desde una unica IP administrativa"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    description = "Salida para administrar las instancias privadas"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-bastion-sg"
  }
}

resource "aws_security_group" "ventas" {
  name        = "${var.project_name}-ventas-sg"
  description = "Prueba controlada dentro del segmento de Ventas"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "SSH unicamente desde el bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  ingress {
    description = "ICMP entre miembros del mismo grupo"
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    self        = true
  }

  egress {
    description = "Respuestas y comunicacion interna de la VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-ventas-sg"
  }
}
