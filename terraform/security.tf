# 1. ALB 전용 보안그룹 (외부 인터넷 80 포트 인입 허용)
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-alb-sg"
  description = "Allow HTTP inbound from Internet"
  vpc_id      = aws_vpc.security_vpc.id

  ingress {
    description = "HTTP from Internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Outbound to internal resources"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# 2. Web 서버 전용 보안그룹 (최소 권한: 오직 ALB 보안그룹 트래픽만 허용)
resource "aws_security_group" "web_sg" {
  name        = "${var.project_name}-web-private-sg"
  description = "Allow traffic ONLY from ALB Security Group"
  vpc_id      = aws_vpc.security_vpc.id

  ingress {
    description     = "HTTP only from ALB SG"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id] # 외부 직접 접근 원천 차단
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-web-private-sg"
  }
}
