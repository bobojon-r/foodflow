module "eks" {
  source = "./modules/eks"

  cluster_name    = local.name
  cluster_version = var.eks_cluster_version
  vpc_id          = aws_vpc.main.id
  subnet_ids      = aws_subnet.private[*].id
  cluster_role_arn = aws_iam_role.eks_cluster.arn
  node_role_arn   = aws_iam_role.eks_nodes.arn
  node_sg_ids     = [aws_security_group.eks_nodes.id]

  node_instance_types = var.eks_node_instance_types
  node_min            = var.eks_node_min
  node_max            = var.eks_node_max
  node_desired        = var.eks_node_desired
}
