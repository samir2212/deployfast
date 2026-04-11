import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { SignedIn, SignedOut, UserButton, useClerk, useAuth } from "@clerk/clerk-react";
import { getSubscriptionStatus, type SubscriptionStatus } from "../api";

export default function Navbar() {
  const { signOut } = useClerk();
  const { getToken, isSignedIn } = useAuth();
  const [sub, setSub] = useState<SubscriptionStatus | null>(null);

  useEffect(() => {
    if (!isSignedIn) return;
    let cancelled = false;
    (async () => {
      try {
        const token = await getToken();
        if (!token || cancelled) return;
        const status = await getSubscriptionStatus(token);
        if (!cancelled) setSub(status);
      } catch {
        // silently fail — badge just won't show
      }
    })();
    return () => { cancelled = true; };
  }, [isSignedIn, getToken]);

  return (
    <nav className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-xl font-bold">
          <img src="/logo.png" alt="Tutaia" className="w-7 h-7 rounded" />
          <span className="bg-gradient-to-r from-primary-400 to-primary-600 bg-clip-text text-transparent">
            Deployfast
          </span>
        </Link>

        <div className="flex items-center gap-4">
          <SignedIn>
            <Link
              to="/dashboard"
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Dashboard
            </Link>
            <Link
              to="/prepare"
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Deploy
            </Link>
            {sub?.active && (
              <Link
                to="/pricing"
                className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-xs font-medium"
              >
                {sub.plan === "builder" ? "Builder" : "Starter"}
                <span className="text-gray-500">
                  {sub.apps_used} / {sub.app_limit}
                </span>
              </Link>
            )}
            <button
              onClick={() => signOut({ redirectUrl: "/" })}
              className="text-sm text-gray-400 hover:text-red-400 transition-colors"
            >
              Sign Out
            </button>
            <UserButton
              afterSignOutUrl="/"
              appearance={{
                variables: {
                  colorBackground: '#1a1a2e',
                  colorInputBackground: '#2a2a40',
                  colorInputText: '#ffffff',
                  colorText: '#ffffff',
                  colorTextSecondary: '#c4c4d4',
                  colorPrimary: '#a78bfa',
                  colorDanger: '#f87171',
                  borderRadius: '8px',
                },
                elements: {
                  card: {
                    backgroundColor: '#1a1a2e',
                    border: '1px solid #3a3a50',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                  },
                  userPreviewMainIdentifier: { color: '#ffffff' },
                  userPreviewSecondaryIdentifier: { color: '#c4c4d4' },
                  userButtonPopoverActionButton: { color: '#e2e2f0' },
                  userButtonPopoverActionButtonText: { color: '#e2e2f0' },
                  userButtonPopoverActionButtonIcon: { color: '#c4c4d4' },
                  userButtonPopoverFooter: { display: 'none' },
                },
              }}
            />
          </SignedIn>
          <SignedOut>
            <Link
              to="/pricing"
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Pricing
            </Link>
            <Link
              to="/sign-in"
              className="text-sm px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-medium"
            >
              Sign In
            </Link>
          </SignedOut>
        </div>
      </div>
    </nav>
  );
}
