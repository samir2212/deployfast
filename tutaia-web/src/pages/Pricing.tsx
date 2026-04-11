import { useAuth, useUser } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { createCheckoutSession, getSubscriptionStatus } from "../api";

const PLANS = [
  {
    name: "Starter",
    price: "$29",
    priceId: "price_1TJ0qgChdqCkGrRmeSXGY3Xa",
    apps: "1 app",
    popular: false,
    features: [
      "Live HTTPS URL",
      "Auto-deployment",
      "Infinite deployments",
      "100% money back guarantee",
    ],
  },
  {
    name: "Builder",
    price: "$39",
    priceId: "price_1TJ0rRChdqCkGrRmYGyFrqUG",
    apps: "2 apps",
    popular: true,
    features: [
      "Live HTTPS URL",
      "Auto-deployment",
      "Infinite deployments",
      "100% money back guarantee",
    ],
  },
];

export default function Pricing() {
  const { isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<string | null>(null);

  // Redirect to dashboard if already subscribed
  useEffect(() => {
    if (!isSignedIn) return;
    let cancelled = false;
    (async () => {
      try {
        const token = await getToken();
        if (!token || cancelled) return;
        const sub = await getSubscriptionStatus(token);
        if (!cancelled && sub.active) navigate("/dashboard", { replace: true });
      } catch {
        // stay on pricing
      }
    })();
    return () => { cancelled = true; };
  }, [isSignedIn, getToken, navigate]);

  async function handleSelect(priceId: string) {
    if (!isSignedIn) {
      navigate("/sign-in?redirect_url=/pricing");
      return;
    }

    setLoading(priceId);
    try {
      const token = await getToken();
      if (!token || !user) throw new Error("Not authenticated");
      const { checkout_url } = await createCheckoutSession(
        priceId,
        user.id,
        token
      );
      window.location.href = checkout_url;
    } catch (err) {
      console.error("Checkout error:", err);
      setLoading(null);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-3">Simple, transparent pricing</h1>
        <p className="text-gray-400 text-lg">
          Deploy your vibe-coded apps with zero DevOps.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`relative rounded-xl p-8 border ${
              plan.popular
                ? "border-primary-500/50 bg-primary-500/5"
                : "border-gray-800 bg-gray-900/50"
            }`}
          >
            {plan.popular && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-primary-600 text-xs font-semibold uppercase tracking-wider">
                Most Popular
              </span>
            )}

            <h2 className="text-2xl font-bold mb-2">{plan.name}</h2>
            <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg mb-4 ${
              plan.popular
                ? "bg-primary-500/20 border border-primary-500/30"
                : "bg-gray-800 border border-gray-700"
            }`}>
              <span className={`text-2xl font-bold ${plan.popular ? "text-primary-300" : "text-white"}`}>
                {plan.apps.split(" ")[0]}
              </span>
              <span className={`text-sm ${plan.popular ? "text-primary-400" : "text-gray-400"}`}>
                {plan.apps.split(" ").slice(1).join(" ")}
              </span>
            </div>

            <div className="mb-6">
              <span className="text-4xl font-bold">{plan.price}</span>
              <span className="text-gray-400">/month</span>
            </div>

            <ul className="space-y-3 mb-8">
              {plan.features.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-gray-300">
                  <span className="text-green-400">&#10003;</span>
                  {f}
                </li>
              ))}
            </ul>

            <button
              onClick={() => handleSelect(plan.priceId)}
              disabled={loading === plan.priceId}
              className={`w-full py-3 rounded-lg font-semibold transition-all ${
                plan.popular
                  ? "bg-primary-600 hover:bg-primary-700"
                  : "bg-gray-800 hover:bg-gray-700 border border-gray-700"
              } disabled:opacity-50`}
            >
              {loading === plan.priceId ? (
                <span className="inline-flex items-center gap-2">
                  <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  Redirecting...
                </span>
              ) : (
                "Get Started"
              )}
            </button>
          </div>
        ))}
      </div>

      <p className="text-center text-gray-500 text-sm mt-8">
        Cancel anytime. No contracts.
      </p>
    </div>
  );
}
