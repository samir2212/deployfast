import logging
import stripe
import resend
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.models import App, Subscription, User

logger = logging.getLogger(__name__)
router = APIRouter()

PLAN_CONFIG = {
    "starter": {"app_limit": 1},
    "builder": {"app_limit": 2},
}


def _get_stripe():
    """Initialize Stripe with secret key from SSM."""
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key
    return stripe


class CheckoutRequest(BaseModel):
    price_id: str
    user_id: str


# ─────────────────────────────────────────────
# Create Stripe Checkout Session
# ─────────────────────────────────────────────
@router.post("/create-checkout-session")
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    s = _get_stripe()

    # Determine plan from price_id
    if body.price_id == settings.stripe_starter_price_id:
        plan = "starter"
    elif body.price_id == settings.stripe_builder_price_id:
        plan = "builder"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid price ID",
        )

    try:
        checkout = s.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": body.price_id, "quantity": 1}],
            success_url="https://deployfast.tutaia.com/payment/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://deployfast.tutaia.com/pricing",
            client_reference_id=current_user.id,
            metadata={
                "user_id": current_user.id,
                "plan": plan,
            },
        )

        return {"checkout_url": checkout.url}

    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


# ─────────────────────────────────────────────
# Subscription Status
# ─────────────────────────────────────────────
@router.get("/subscription-status")
async def subscription_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get active subscription
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()

    if not sub:
        return {
            "active": False,
            "plan": None,
            "app_limit": 0,
            "apps_used": 0,
        }

    # Count user's current apps
    count_result = await db.execute(
        select(func.count(App.id)).where(App.user_id == current_user.id)
    )
    apps_used = count_result.scalar() or 0

    return {
        "active": True,
        "plan": sub.plan,
        "app_limit": sub.app_limit,
        "apps_used": apps_used,
    }


# ─────────────────────────────────────────────
# Verify Payment (after Stripe redirect)
# ─────────────────────────────────────────────
@router.get("/verify")
async def verify_payment(
    session_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = _get_stripe()

    try:
        checkout = s.checkout.Session.retrieve(session_id)
    except Exception as e:
        logger.error(f"Stripe session retrieve error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session",
        )

    if checkout.payment_status != "paid":
        return {"success": False, "plan": None}

    plan = checkout.metadata.get("plan", "starter")
    app_limit = PLAN_CONFIG.get(plan, {}).get("app_limit", 1)

    # Check if subscription already exists for this session
    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_checkout_session_id == session_id
        )
    )
    existing = result.scalar_one_or_none()

    if not existing:
        # Create subscription record
        sub = Subscription(
            user_id=current_user.id,
            stripe_customer_id=checkout.customer,
            stripe_subscription_id=checkout.subscription,
            stripe_checkout_session_id=session_id,
            plan=plan,
            status="active",
            app_limit=app_limit,
        )
        db.add(sub)
        await db.commit()
        logger.info(f"Subscription created: user={current_user.id} plan={plan}")

        # Send welcome email
        _send_welcome_email(current_user.email, plan, app_limit)

    return {"success": True, "plan": plan}


def _send_welcome_email(email: str, plan: str, app_limit: int):
    """Send a welcome email after successful payment."""
    try:
        settings = get_settings()
        resend.api_key = settings.resend_api_key

        plan_name = plan.capitalize()
        resend.Emails.send({
            "from": "Deployfast <noreply@deployfast.tutaia.com>",
            "to": [email],
            "subject": f"Welcome to Deployfast - {plan_name} Plan Activated! 🚀",
            "html": f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px; color: #e5e5e5; background-color: #0a0a0f;">
              <div style="text-align: center; margin-bottom: 32px;">
                <span style="font-size: 48px;">🚀</span>
                <h1 style="color: #ffffff; font-size: 28px; margin: 16px 0 0;">Welcome to Deployfast!</h1>
              </div>

              <div style="background: #111118; border: 1px solid #1e1e2e; border-radius: 12px; padding: 32px; margin-bottom: 24px;">
                <p style="color: #a0aec0; font-size: 16px; line-height: 1.6; margin: 0 0 16px;">
                  Your payment was successful and your <strong style="color: #a78bfa;">{plan_name} Plan</strong> is now active.
                </p>

                <div style="background: #0a0a0f; border-radius: 8px; padding: 16px; margin: 20px 0;">
                  <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                      <td style="color: #a0aec0; padding: 6px 0; font-size: 14px;">Plan</td>
                      <td style="color: #ffffff; padding: 6px 0; font-size: 14px; text-align: right; font-weight: 600;">{plan_name}</td>
                    </tr>
                    <tr>
                      <td style="color: #a0aec0; padding: 6px 0; font-size: 14px;">App slots</td>
                      <td style="color: #ffffff; padding: 6px 0; font-size: 14px; text-align: right; font-weight: 600;">{app_limit}</td>
                    </tr>
                    <tr>
                      <td style="color: #a0aec0; padding: 6px 0; font-size: 14px;">Status</td>
                      <td style="padding: 6px 0; font-size: 14px; text-align: right;">
                        <span style="color: #34d399; font-weight: 600;">Active &#10003;</span>
                      </td>
                    </tr>
                  </table>
                </div>

                <p style="color: #a0aec0; font-size: 16px; line-height: 1.6; margin: 16px 0 0;">
                  You're ready to deploy your first app. Just zip your project, upload it, and get a live HTTPS URL in minutes.
                </p>
              </div>

              <div style="text-align: center; margin-bottom: 32px;">
                <a href="https://deployfast.tutaia.com/prepare"
                   style="display: inline-block; background: #7c3aed; color: #ffffff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">
                  Deploy Your First App
                </a>
              </div>

              <div style="text-align: center; border-top: 1px solid #1e1e2e; padding-top: 24px;">
                <p style="color: #64748b; font-size: 13px; margin: 0;">
                  Tutaia — Deploy vibe-coded apps to the cloud.
                </p>
              </div>
            </div>
            """,
        })
        logger.info(f"Welcome email sent to {email}")
    except Exception as e:
        # Don't fail the payment flow if email fails
        logger.error(f"Failed to send welcome email to {email}: {e}")
