# Las subredes privadas no tienen NAT Gateway. Los repositorios de Amazon Linux
# 2023 se publican en buckets S3 administrados por AWS, por lo que un VPC Gateway
# Endpoint de S3 permite ejecutar dnf desde Data Center sin salida a Internet.
# El endpoint Gateway no tiene costo por hora ni por GB (a diferencia de NAT).
#
# Solo se crea durante la ventana autorizada junto con el cómputo de Fase 2.

resource "aws_vpc_endpoint" "s3" {
  count = var.enable_phase2_compute ? 1 : 0

  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  # Política mínima: solo lectura de los repositorios de Amazon Linux 2023.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AmazonLinux2023Repos"
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::al2023-repos-${var.aws_region}-de612dc2",
          "arn:aws:s3:::al2023-repos-${var.aws_region}-de612dc2/*",
        ]
      }
    ]
  })

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-s3-gateway-endpoint"
    Purpose = "al2023-repos"
  })
}
