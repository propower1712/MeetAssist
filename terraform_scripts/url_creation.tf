# Fetch existing Route 53 hosted zone by domain name
data "aws_route53_zone" "main" {
  name = "meet-assist.click"
}

resource "aws_acm_certificate" "my_cert" {
  domain_name       = "meet-assist.click"
  validation_method = "DNS"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.my_cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      value  = dvo.resource_record_value
    }
  }

  zone_id = data.aws_route53_zone.main.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.value]
  ttl     = 300

  lifecycle {
    prevent_destroy = true
  }
}

# Root domain alias record pointing to the ALB using an A record
resource "aws_route53_record" "app_alias" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "meet-assist.click"
  type    = "A"
  alias {
    name                   = aws_lb.app_lb.dns_name
    zone_id                = aws_lb.app_lb.zone_id
    evaluate_target_health = false
  }
}

output "app_url" {
  description = "The URL of the application"
  value       = "https://meet-assist.click"
}