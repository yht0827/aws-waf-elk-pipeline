# 최신 Amazon Linux 2023 AMI 자동 조회
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

# 1. Nginx 웹 서버 인스턴스 A (가용영역: ap-northeast-2a)
resource "aws_instance" "web_a" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public_a.id
  vpc_security_group_ids = [aws_security_group.web_sg.id]

  user_data = templatefile("${path.module}/templates/user_data.sh.tpl", {
    node_name = "Backend Server #1"
  })

  tags = {
    Name = "${var.project_name}-web-server-a"
  }
}

# 2. Nginx 웹 서버 인스턴스 C (가용영역: ap-northeast-2c)
resource "aws_instance" "web_c" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public_c.id
  vpc_security_group_ids = [aws_security_group.web_sg.id]

  user_data = templatefile("${path.module}/templates/user_data.sh.tpl", {
    node_name = "Backend Server #2"
  })

  tags = {
    Name = "${var.project_name}-web-server-c"
  }
}
