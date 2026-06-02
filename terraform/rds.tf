# Один RDS инстанс, три базы данных (database-per-service через разные credentials)

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier        = "${local.name}-postgres"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = var.db_instance_class
  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "foodflow"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  deletion_protection = false  # true в продакшне
  skip_final_snapshot = true   # false в продакшне

  tags = { Name = "${local.name}-postgres" }
}

# Создаём отдельные БД для каждого сервиса через null_resource
# (в реальном проекте через Flyway или init-container)
resource "aws_ssm_parameter" "db_auth_url" {
  name  = "/${local.name}/auth-service/DATABASE_URL"
  type  = "SecureString"
  value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.main.address}:5432/auth_db"
}

resource "aws_ssm_parameter" "db_restaurant_url" {
  name  = "/${local.name}/restaurant-service/DATABASE_URL"
  type  = "SecureString"
  value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.main.address}:5432/restaurant_db"
}

resource "aws_ssm_parameter" "db_order_url" {
  name  = "/${local.name}/order-service/DATABASE_URL"
  type  = "SecureString"
  value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.main.address}:5432/order_db"
}
