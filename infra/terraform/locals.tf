locals {
  availability_zone = data.aws_availability_zones.available.names[0]

  subnets = {
    visitas = {
      cidr   = "10.10.0.0/26"
      public = true
      phase  = 1
    }
    ventas = {
      cidr   = "10.10.0.64/26"
      public = false
      phase  = 1
    }
    ti = {
      cidr   = "10.10.0.128/27"
      public = false
      phase  = 1
    }
    datacenter = {
      cidr   = "10.10.0.160/28"
      public = false
      phase  = 1
    }
    administracion = {
      cidr   = "10.10.0.176/28"
      public = true
      phase  = 1
    }
    dmz = {
      cidr   = "10.10.0.192/27"
      public = true
      phase  = 2
    }
  }

  phase2_reserved_cidr = "10.10.0.224/27"

  phase2_service_ips = var.phase2_private_ips

  phase2_tags = {
    Project     = "CC3067-Fase-2"
    Group       = "Grupo-1"
    Environment = "academic-poc"
    ManagedBy   = "Terraform"
    Phase       = "2"
    DeleteAfter = var.phase2_delete_after
  }

  common_tags = {
    Project     = "CC3067-Fase-1"
    Group       = "Grupo-1"
    Environment = "academic-poc"
    ManagedBy   = "Terraform"
    DeleteAfter = "2026-10-22"
  }
}
