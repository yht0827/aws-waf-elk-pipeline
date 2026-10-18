# 1. AWS WAFv2 Web ACL (L7 공격 인라인 차단 룰셋)
resource "aws_wafv2_web_acl" "main_waf" {
  name        = "${var.project_name}-web-acl"
  description = "Multi-layered WAF rules for SQLi, XSS, Scanner UA, and Rate Limiting with Custom 403 Page"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # 커스텀 403 차단 응답 페이지 (외부 템플릿 파일 templates/waf_403.html 로드)
  custom_response_body {
    key          = "custom_403_html"
    content_type = "TEXT_HTML"
    content      = file("${path.module}/templates/waf_403.html")
  }



  # Rule 0: 커스텀 SQLi & XSS 인라인 탐지 및 커스텀 403 응답
  rule {
    name     = "Custom-Inline-Web-Attack-Defense"
    priority = 5
    action {
      block {
        custom_response {
          response_code            = 403
          custom_response_body_key = "custom_403_html"
        }
      }
    }
    statement {
      or_statement {
        statement {
          sqli_match_statement {
            field_to_match {
              query_string {}
            }
            text_transformation {
              priority = 0
              type     = "URL_DECODE"
            }
            text_transformation {
              priority = 1
              type     = "LOWERCASE"
            }
          }
        }
        statement {
          xss_match_statement {
            field_to_match {
              query_string {}
            }
            text_transformation {
              priority = 0
              type     = "URL_DECODE"
            }
            text_transformation {
              priority = 1
              type     = "LOWERCASE"
            }
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CustomWebAttackMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 1: AWS Managed Common Rule Set (XSS, LFI 등 방어)
  rule {
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    priority = 10
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: AWS Managed SQL Injection Rule Set
  rule {
    name     = "AWS-AWSManagedRulesSQLiRuleSet"
    priority = 20
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLiRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: 비정상 취약점 스캐너 User-Agent 차단 (sqlmap, nikto)
  rule {
    name     = "Custom-Block-Scanner-UserAgent"
    priority = 30
    action {
      block {
        custom_response {
          response_code            = 403
          custom_response_body_key = "custom_403_html"
        }
      }
    }
    statement {
      or_statement {
        statement {
          byte_match_statement {
            search_string         = "sqlmap"
            positional_constraint = "CONTAINS"
            field_to_match {
              single_header {
                name = "user-agent"
              }
            }
            text_transformation {
              priority = 0
              type     = "LOWERCASE"
            }
          }
        }
        statement {
          byte_match_statement {
            search_string         = "nikto"
            positional_constraint = "CONTAINS"
            field_to_match {
              single_header {
                name = "user-agent"
              }
            }
            text_transformation {
              priority = 0
              type     = "LOWERCASE"
            }
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BlockScannerUAMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: Rate-based Rule (단시간 과도한 요청 IP 자동 차단)
  rule {
    name     = "Custom-RateLimit-DDoS-Protection"
    priority = 40
    action {
      block {
        custom_response {
          response_code            = 403
          custom_response_body_key = "custom_403_html"
        }
      }
    }
    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitMetric"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "SecPipelineWebACL"
    sampled_requests_enabled   = true
  }

  tags = {
    Name = "${var.project_name}-web-acl"
  }
}

# 2. WAF를 ALB에 연결
resource "aws_wafv2_web_acl_association" "alb_assoc" {
  resource_arn = aws_lb.alb.arn
  web_acl_arn  = aws_wafv2_web_acl.main_waf.arn
}

# 3. WAF 실시간 로그 수집용 CloudWatch Log Group
resource "aws_cloudwatch_log_group" "waf_log_group" {
  name              = "aws-waf-logs-${var.project_name}"
  retention_in_days = var.waf_log_retention_days
}

resource "aws_wafv2_web_acl_logging_configuration" "waf_logging" {
  log_destination_configs = [aws_cloudwatch_log_group.waf_log_group.arn]
  resource_arn            = aws_wafv2_web_acl.main_waf.arn
}
