resource "aws_key_pair" "lab" {
  count = var.enable_compute ? 1 : 0

  key_name   = "${var.project_name}-key"
  public_key = file(var.public_key_path)

  lifecycle {
    precondition {
      condition     = var.public_key_path != ""
      error_message = "Defina public_key_path cuando enable_compute sea true."
    }
  }

  tags = {
    Name = "${var.project_name}-key"
  }
}

resource "aws_instance" "bastion" {
  count = var.enable_compute ? 1 : 0

  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.segments["administracion"].id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  key_name                    = aws_key_pair.lab[0].key_name
  associate_public_ip_address = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    encrypted   = true
    volume_size = 8
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.project_name}-bastion"
    Role = "temporary-management"
  }
}

resource "aws_instance" "ventas" {
  count = var.enable_compute ? 2 : 0

  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.segments["ventas"].id
  vpc_security_group_ids      = [aws_security_group.ventas.id]
  key_name                    = aws_key_pair.lab[0].key_name
  associate_public_ip_address = false

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    encrypted   = true
    volume_size = 8
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.project_name}-ventas-${count.index + 1}"
    Role = "connectivity-test"
  }
}
