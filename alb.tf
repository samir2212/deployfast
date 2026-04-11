# ─────────────────────────────────────────────
# Application Load Balancer
# Shared across ALL user app ECS tasks
# One ALB, many target groups, many listener rules
# ─────────────────────────────────────────────
resource "aws_lb" "main" {
  name               = "tutaia-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false # Set to true after validation phase

  tags = {
    Name = "tutaia-alb"
  }
}

# ─────────────────────────────────────────────
# HTTP Listener - redirects all traffic to HTTPS
# ─────────────────────────────────────────────
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ─────────────────────────────────────────────
# HTTPS Listener
# Default action returns 404 - only named subdomains
# that have a listener rule will get traffic
# ─────────────────────────────────────────────
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.wildcard.certificate_arn

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "App not found"
      status_code  = "404"
    }
  }
}

# ─────────────────────────────────────────────
# Platform API Target Group
# Your deployment engine sits behind the ALB too
# ─────────────────────────────────────────────
resource "aws_lb_target_group" "platform_api" {
  name        = "tutaia-platform-api-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name = "tutaia-platform-api-tg"
  }
}

# ─────────────────────────────────────────────
# Platform API Listener Rule
# api.tutaia.com → platform API
# ─────────────────────────────────────────────
resource "aws_lb_listener_rule" "platform_api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.platform_api.arn
  }

  condition {
    host_header {
      values = ["api.ai-deploy.${var.domain_name}"]
    }
  }
}

# Route53 record for api.tutaia.com
resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "api.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
