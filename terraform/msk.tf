resource "aws_msk_cluster" "main" {
  cluster_name           = "${local.name}-kafka"
  kafka_version          = var.msk_kafka_version
  number_of_broker_nodes = 2

  broker_node_group_info {
    instance_type   = var.msk_instance_type
    client_subnets  = slice(aws_subnet.private[*].id, 0, 2)
    security_groups = [aws_security_group.msk.id]

    storage_info {
      ebs_storage_info {
        volume_size = 20
      }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "PLAINTEXT"
      in_cluster    = true
    }
  }

  configuration_info {
    arn      = aws_msk_configuration.main.arn
    revision = aws_msk_configuration.main.latest_revision
  }

  tags = { Name = "${local.name}-kafka" }
}

resource "aws_msk_configuration" "main" {
  name              = "${local.name}-kafka-config"
  kafka_versions    = [var.msk_kafka_version]
  server_properties = <<-EOT
    auto.create.topics.enable=true
    default.replication.factor=2
    min.insync.replicas=1
    num.partitions=3
    log.retention.hours=168
  EOT
}

resource "aws_ssm_parameter" "kafka_bootstrap" {
  name  = "/${local.name}/kafka/BOOTSTRAP_SERVERS"
  type  = "String"
  value = aws_msk_cluster.main.bootstrap_brokers
}
