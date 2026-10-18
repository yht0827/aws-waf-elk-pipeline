# 1. Application Load Balancer
resource "aws_lb" "alb" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_c.id]

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# 2. ALB Target Group (백엔드 웹서버 연결)
resource "aws_lb_target_group" "tg" {
  name     = "${var.project_name}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.security_vpc.id

  health_check {
    path                = "/"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
    interval            = 10
  }

  tags = {
    Name = "${var.project_name}-tg"
  }
}

# 3. Target Group에 Multi-AZ EC2 인스턴스 2대 등록
resource "aws_lb_target_group_attachment" "web_a_attach" {
  target_group_arn = aws_lb_target_group.tg.arn
  target_id        = aws_instance.web_a.id
  port             = 80
}

resource "aws_lb_target_group_attachment" "web_c_attach" {
  target_group_arn = aws_lb_target_group.tg.arn
  target_id        = aws_instance.web_c.id
  port             = 80
}


# 4. ALB HTTP 리스너 (포트 80 트래픽을 Target Group으로 포워딩)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }
}
