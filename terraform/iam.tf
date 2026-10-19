# 1. EC2 인스턴스용 IAM Role (AssumeRole)
resource "aws_iam_role" "ec2_ssm_role" {
  name        = "${var.project_name}-ec2-ssm-role"
  description = "IAM role for EC2 instances to enable AWS Systems Manager and CloudWatch logging"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ec2-ssm-role"
  }
}

# 2. AWS Systems Manager(SSM) 관리형 정책 연결 (22번 SSH 포트 없이 세션 접속 가능)
resource "aws_iam_role_policy_attachment" "ssm_policy_attach" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# 3. EC2에 부여할 IAM 인스턴스 프로파일
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-instance-profile"
  role = aws_iam_role.ec2_ssm_role.name

  tags = {
    Name = "${var.project_name}-ec2-instance-profile"
  }
}
