# ─────────────────────────────────────────────
# Bastion Host - SSH tunnel to private RDS
# Connect via: ssh -i ~/.ssh/tutaia-bastion.pem ec2-user@<bastion_ip> -L 5432:<rds_endpoint>:5432
# Then use your DB GUI on localhost:5432
# ─────────────────────────────────────────────

# ─── Key Pair ────────────────────────────────
resource "aws_key_pair" "bastion" {
  key_name   = "tutaia-bastion-key"
  public_key = var.bastion_public_key
}

# ─── Security Group ─────────────────────────
resource "aws_security_group" "bastion" {
  name        = "tutaia-bastion-sg"
  description = "Security group for bastion host - SSH access"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "tutaia-bastion-sg"
  }
}

# ─── Allow bastion to access RDS ─────────────
resource "aws_security_group_rule" "rds_from_bastion" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.bastion.id
  description              = "Postgres from bastion host"
}

# ─── Get latest Amazon Linux 2023 AMI ───────
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ─── EC2 Instance ────────────────────────────
resource "aws_instance" "bastion" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t3.micro"
  key_name                    = aws_key_pair.bastion.key_name
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  associate_public_ip_address = true

  tags = {
    Name = "tutaia-bastion"
  }
}
