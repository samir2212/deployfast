import { SignUp } from "@clerk/clerk-react";
import { useSearchParams } from "react-router-dom";

export default function SignUpPage() {
  const [searchParams] = useSearchParams();
  const redirectUrl = searchParams.get("redirect_url") || "/dashboard";

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] px-4">
      <SignUp
        routing="path"
        path="/sign-up"
        signInUrl={`/sign-in${redirectUrl !== "/dashboard" ? `?redirect_url=${redirectUrl}` : ""}`}
        afterSignUpUrl={redirectUrl}
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
            headerTitle: { color: '#ffffff', fontSize: '24px' },
            headerSubtitle: { color: '#c4c4d4' },
            formFieldLabel: { color: '#e2e2f0' },
            formFieldInput: {
              backgroundColor: '#2a2a40',
              borderColor: '#4a4a60',
              color: '#ffffff',
            },
            socialButtonsBlockButton: {
              backgroundColor: '#2a2a40',
              borderColor: '#4a4a60',
              color: '#ffffff',
            },
            socialButtonsBlockButtonText: { color: '#e2e2f0' },
            dividerLine: { backgroundColor: '#3a3a50' },
            dividerText: { color: '#c4c4d4' },
            footerActionLink: { color: '#a78bfa' },
            footerActionText: { color: '#c4c4d4' },
            identityPreviewText: { color: '#ffffff' },
            identityPreviewEditButton: { color: '#a78bfa' },
            formButtonPrimary: {
              backgroundColor: '#7c3aed',
              color: '#ffffff',
              fontWeight: '600',
            },
          },
        }}
      />
    </div>
  );
}
