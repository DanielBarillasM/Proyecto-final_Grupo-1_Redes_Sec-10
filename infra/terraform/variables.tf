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
