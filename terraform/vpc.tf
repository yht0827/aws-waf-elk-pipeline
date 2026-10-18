# 1. VPC 생성
resource "aws_vpc" "security_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# 2. 인터넷 게이트웨이 (외부 인터넷 연결)
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.security_vpc.id
  tags = {
    Name = "${var.project_name}-igw"
  }
}

# 3. 퍼블릭 서브넷 2개 (ALB용 다중 가용영역)
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.security_vpc.id
  cidr_block              = var.public_subnet_cidrs["a"]
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.project_name}-public-subnet-a"
  }
}

resource "aws_subnet" "public_c" {
  vpc_id                  = aws_vpc.security_vpc.id
  cidr_block              = var.public_subnet_cidrs["c"]
  availability_zone       = "${var.aws_region}c"
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.project_name}-public-subnet-c"
  }
}

# 4. 프라이빗 격리 서브넷 (내부 워크로드용)
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.security_vpc.id
  cidr_block        = var.private_subnet_cidrs["a"]
  availability_zone = "${var.aws_region}a"
  tags = {
    Name = "${var.project_name}-private-subnet-a"
  }
}

# 5. 퍼블릭 라우팅 테이블 및 서브넷 연결
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.security_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_c" {
  subnet_id      = aws_subnet.public_c.id
  route_table_id = aws_route_table.public_rt.id
}
