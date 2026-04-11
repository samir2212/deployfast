# ─────────────────────────────────────────────
# Route53 - assumes tutaia.com is already
# registered and hosted zone exists in your account
# ─────────────────────────────────────────────
data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

# ─────────────────────────────────────────────
# ACM Wildcard Certificate for *.tutaia.com
# This covers every user app subdomain automatically
# ─────────────────────────────────────────────
resource "aws_acm_certificate" "wildcard" {
  domain_name               = "${var.platform_subdomain}.${var.domain_name}"
  subject_alternative_names = ["*.${var.platform_subdomain}.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "tutaia-wildcard-cert"
  }
}

# ─────────────────────────────────────────────
# DNS validation records for ACM
# ─────────────────────────────────────────────
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.wildcard.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "wildcard" {
  certificate_arn         = aws_acm_certificate.wildcard.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# ─────────────────────────────────────────────
# Wildcard DNS record pointing to ALB
# *.tutaia.com → ALB
# Every user app gets {appid}.tutaia.com automatically
# ─────────────────────────────────────────────
resource "aws_route53_record" "wildcard" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "*.${var.platform_subdomain}.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# Platform root: ai-deploy.tutaia.com → ALB
resource "aws_route53_record" "platform_root" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "${var.platform_subdomain}.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
