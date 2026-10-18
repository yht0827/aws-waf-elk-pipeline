output "alb_dns_name" {
  description = "Public DNS URL of the Application Load Balancer"
  value       = "http://${aws_lb.alb.dns_name}"
}

output "waf_acl_name" {
  description = "Name of the AWS WAF Web ACL"
  value       = aws_wafv2_web_acl.main_waf.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch Log Group storing WAF logs"
  value       = aws_cloudwatch_log_group.waf_log_group.name
}
