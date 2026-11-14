variable "aws_region" {
  description = "Región AWS para el prototipo."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefijo para nombres y etiquetas."
  type        = string
  default     = "rednova-fase1"
}

variable "vpc_cidr" {
  description = "Bloque principal de la VPC."
  type        = string
  default     = "10.10.0.0/24"
}

variable "enable_compute" {
  description = "Crea el bastión y dos instancias privadas de Ventas para la prueba."
  type        = bool
  default     = false
}

variable "admin_cidr" {
  description = "IP pública autorizada para SSH al bastión, obligatoriamente /32."
  type        = string
  default     = "203.0.113.10/32"

  validation {
    condition     = can(cidrhost(var.admin_cidr, 0)) && endswith(var.admin_cidr, "/32") && var.admin_cidr != "0.0.0.0/32"
    error_message = "admin_cidr debe ser una IPv4 válida con prefijo /32."
  }
}

variable "public_key_path" {
  description = "Ruta local de la llave pública que se registrará temporalmente en EC2."
  type        = string
  default     = ""
}

variable "instance_type" {
  description = "Tipo de instancia pequeño para la prueba de concepto."
  type        = string
  default     = "t3.micro"
}

variable "phase2_project_name" {
  description = "Prefijo para los recursos nuevos de la Fase 2."
  type        = string
  default     = "rednova-fase2"
}

variable "enable_phase2_compute" {
  description = "Habilita las instancias de servicios y prueba de Fase 2. Debe permanecer en false fuera de una ventana autorizada."
  type        = bool
  default     = false
}

variable "phase2_instance_type" {
  description = "Tipo de instancia pequeño para los servicios de Fase 2."
  type        = string
  default     = "t3.micro"
}

variable "phase2_delete_after" {
  description = "Fecha ISO prevista para retirar los recursos temporales de Fase 2."
  type        = string
  default     = "2026-11-16"

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.phase2_delete_after))
    error_message = "phase2_delete_after debe usar el formato YYYY-MM-DD."
  }
}

variable "internal_domain" {
  description = "Dominio interno administrado por BIND9. Se evita .local para no interferir con mDNS."
  type        = string
  default     = "rednova.internal"

  validation {
    condition = (
      can(regex("^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$", var.internal_domain)) &&
      !endswith(lower(var.internal_domain), ".local")
    )
    error_message = "internal_domain debe ser un nombre DNS válido y no debe terminar en .local."
  }
}

variable "public_domain" {
  description = "Dominio o subdominio público de la web de Ventas. Puede quedar vacío durante la validación local."
  type        = string
  default     = ""

  validation {
    condition = (
      var.public_domain == "" ||
      can(regex("^[A-Za-z0-9][A-Za-z0-9.-]*\\.[A-Za-z]{2,}$", var.public_domain))
    )
    error_message = "public_domain debe estar vacío o contener un dominio público válido."
  }
}

variable "enable_https" {
  description = "Documenta si la web pública habilitará HTTPS. Solo debe activarse cuando public_domain ya resuelva."
  type        = bool
  default     = false
}

variable "phase2_private_ips" {
  description = "Direcciones privadas propuestas para los servicios y clientes de prueba de Fase 2."
  type = object({
    visitas_client = string
    ti_client      = string
    dns            = string
    intranet       = string
    public_web     = string
  })

  default = {
    visitas_client = "10.10.0.4"
    ti_client      = "10.10.0.132"
    dns            = "10.10.0.164"
    intranet       = "10.10.0.165"
    public_web     = "10.10.0.196"
  }

  validation {
    condition     = alltrue([for ip in values(var.phase2_private_ips) : can(cidrhost("${ip}/32", 0))])
    error_message = "Todas las phase2_private_ips deben ser direcciones IPv4 válidas."
  }
}
