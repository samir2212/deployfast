import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { SignedIn, SignedOut, useAuth } from "@clerk/clerk-react";
import Navbar from "./components/Navbar";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import Prepare from "./pages/Prepare";
import Deploy from "./pages/Deploy";
import SignInPage from "./pages/SignIn";
import SignUpPage from "./pages/SignUp";
import Pricing from "./pages/Pricing";
import PaymentSuccess from "./pages/PaymentSuccess";
import { getSubscriptionStatus } from "./api";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <Navigate to="/sign-in" replace />
      </SignedOut>
    </>
  );
}

function PaidRoute({ children }: { children: React.ReactNode }) {
  const { getToken, isSignedIn } = useAuth();
  const [checking, setChecking] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);

  useEffect(() => {
    if (!isSignedIn) {
      setChecking(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const token = await getToken();
        if (!token || cancelled) return;
        const sub = await getSubscriptionStatus(token);
        if (!cancelled) setHasAccess(sub.active);
      } catch {
        // If check fails, allow access (don't lock out on API errors)
        if (!cancelled) setHasAccess(true);
      } finally {
        if (!cancelled) setChecking(false);
      }
    })();
    return () => { cancelled = true; };
  }, [isSignedIn, getToken]);

  return (
    <>
      <SignedOut>
        <Navigate to="/sign-in?redirect_url=/pricing" replace />
      </SignedOut>
      <SignedIn>
        {checking ? (
          <div className="flex items-center justify-center py-24">
            <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full" />
          </div>
        ) : hasAccess ? (
          children
        ) : (
          <Navigate to="/pricing" replace />
        )}
      </SignedIn>
    </>
  );
}

export default function App() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <Routes>
        {/* Signed-in users go to dashboard (PaidRoute will redirect to /pricing if no sub) */}
        <Route
          path="/"
          element={
            <>
              <SignedIn>
                <Navigate to="/dashboard" replace />
              </SignedIn>
              <SignedOut>
                <Landing />
              </SignedOut>
            </>
          }
        />
        <Route path="/sign-in/*" element={<SignInPage />} />
        <Route path="/sign-up/*" element={<SignUpPage />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route
          path="/payment/success"
          element={
            <ProtectedRoute>
              <PaymentSuccess />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <PaidRoute>
              <Dashboard />
            </PaidRoute>
          }
        />
        <Route
          path="/prepare"
          element={
            <PaidRoute>
              <Prepare />
            </PaidRoute>
          }
        />
        <Route
          path="/deploy"
          element={
            <PaidRoute>
              <Deploy />
            </PaidRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
