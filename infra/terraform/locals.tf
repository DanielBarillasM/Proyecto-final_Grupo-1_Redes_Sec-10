locals {
  availability_zone = data.aws_availability_zones.available.names[0]

  subnets = {
    visitas = {
      cidr   = "10.10.0.0/26"
      public = true
    }
    ventas = {
      cidr   = "10.10.0.64/26"
      public = false
    }
    ti = {
      cidr   = "10.10.0.128/27"
      public = false
    }
    datacenter = {
      cidr   = "10.10.0.160/28"
      public = false
    }
    administracion = {
      cidr   = "10.10.0.176/28"
      public = true
    }
  }

  common_tags = {
    Project     = "CC3067-Fase-1"
    Group       = "Grupo-1"
    Environment = "academic-poc"
    ManagedBy   = "Terraform"
    DeleteAfter = "2026-10-19"
  }
}
