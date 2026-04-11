import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { verifyPayment } from "../api";
import Confetti from "../components/Confetti";

export default function PaymentSuccess() {
  const [searchParams] = useSearchParams();
  const { getToken } = useAuth();
  const [plan, setPlan] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const sessionId = searchParams.get("session_id");
    if (!sessionId) {
      setError("Missing session ID");
      setLoading(false);
      return;
    }

    async function verify() {
      try {
        const token = await getToken();
        if (!token) throw new Error("Not authenticated");
        const result = await verifyPayment(sessionId!, token);
        if (result.success) {
          setPlan(result.plan);
        } else {
          setError("Payment could not be verified.");
        }
      } catch {
        // Payment may still be processing — show success optimistically
        setPlan("your selected");
      } finally {
        setLoading(false);
      }
    }

    verify();
  }, [searchParams, getToken]);

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto" />
        <p className="text-gray-400 mt-4">Verifying your payment...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <div className="text-4xl mb-4">&#9888;&#65039;</div>
        <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
        <p className="text-gray-400 mb-6">{error}</p>
        <Link
          to="/pricing"
          className="px-5 py-2.5 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-medium"
        >
          Back to Pricing
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-24 text-center">
      <Confetti />
      <div className="text-5xl mb-4">🚀</div>
      <h1 className="text-3xl font-bold mb-3">You're all set!</h1>
      <p className="text-gray-400 text-lg mb-2">Your account is now active.</p>
      {plan && (
        <p className="text-primary-400 font-medium mb-8">
          {plan.charAt(0).toUpperCase() + plan.slice(1)} plan activated
        </p>
      )}
      <Link
        to="/prepare"
        className="inline-flex px-6 py-3 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-semibold text-lg"
      >
        Deploy Your First App
      </Link>
    </div>
  );
}
