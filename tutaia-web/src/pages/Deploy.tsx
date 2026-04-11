import { useState, useCallback, useRef, useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";
import { deployApp, getApp, listApps, getSubscriptionStatus, type App, type SubscriptionStatus } from "../api";
import FileUpload from "../components/FileUpload";
import StatusBadge from "../components/StatusBadge";
import Confetti from "../components/Confetti";

type Phase = "form" | "deploying" | "done";

export default function Deploy() {
  const { getToken } = useAuth();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [subdomain, setSubdomain] = useState("");
  const [subdomainError, setSubdomainError] = useState("");
  const [phase, setPhase] = useState<Phase>("form");
  const [app, setApp] = useState<App | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sub, setSub] = useState<SubscriptionStatus | null>(null);
  const [subLoading, setSubLoading] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  // Check subscription on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getToken();
        if (!token || cancelled) return;
        const status = await getSubscriptionStatus(token);
        if (!cancelled) setSub(status);
      } catch {
        // subscription check failed — allow proceeding
      } finally {
        if (!cancelled) setSubLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [getToken]);

  const startPolling = useCallback(
    (appId: string) => {
      pollRef.current = setInterval(async () => {
        try {
          const token = await getToken();
          if (!token) return;
          const updated = await getApp(appId, token);
          setApp(updated);
          if (updated.status === "running" || updated.status === "failed") {
            clearInterval(pollRef.current);
            if (updated.status === "running") setPhase("done");
          }
        } catch {
          // keep polling on transient errors
        }
      }, 5000);
    },
    [getToken]
  );

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  function validateSubdomain(value: string): string {
    if (!value) return "Domain name is required";
    if (value.length < 3) return "Must be at least 3 characters";
    if (value.length > 40) return "Must be 40 characters or less";
    if (!/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(value))
      return "Only lowercase letters, numbers, and hyphens. Cannot start or end with a hyphen.";
    return "";
  }

  function handleSubdomainChange(value: string) {
    // Auto-lowercase, strip spaces and special chars except hyphens
    const cleaned = value.toLowerCase().replace(/[^a-z0-9-]/g, "");
    setSubdomain(cleaned);
    if (cleaned) setSubdomainError(validateSubdomain(cleaned));
    else setSubdomainError("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !name.trim() || !subdomain) return;

    const domainErr = validateSubdomain(subdomain);
    if (domainErr) {
      setSubdomainError(domainErr);
      return;
    }

    setError("");
    setSubmitting(true);

    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      const created = await deployApp(file, name.trim(), token, subdomain);
      setApp(created);
      setPhase("deploying");
      startPolling(created.id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Deployment failed";
      // If we get a network error like "Load failed", the upload may have
      // succeeded — check if the app was created and redirect to dashboard.
      if (msg === "Load failed" || msg.includes("Failed to fetch")) {
        try {
          const token = await getToken();
          if (token) {
            const apps = await listApps(token);
            const found = apps.find(
              (a) => a.name === name.trim() && a.status === "building"
            );
            if (found) {
              setApp(found);
              setPhase("deploying");
              startPolling(found.id);
              setSubmitting(false);
              return;
            }
          }
        } catch {
          // fall through to show original error
        }
      }
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  // Subscription gate
  if (!subLoading && sub && !sub.active) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <div className="text-4xl mb-4">🔒</div>
        <h2 className="text-xl font-semibold mb-2">No active plan</h2>
        <p className="text-gray-400 mb-6">You need an active plan to deploy apps.</p>
        <Link to="/pricing" className="px-6 py-3 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-semibold">
          Choose a Plan
        </Link>
      </div>
    );
  }

  if (!subLoading && sub && sub.apps_used >= sub.app_limit) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <div className="text-4xl mb-4">📦</div>
        <h2 className="text-xl font-semibold mb-2">App limit reached</h2>
        <p className="text-gray-400 mb-6">
          You've used {sub.apps_used} of {sub.app_limit} app slots. Upgrade your plan for more.
        </p>
        <Link to="/pricing" className="px-6 py-3 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-semibold">
          Upgrade Plan
        </Link>
      </div>
    );
  }

  if (phase === "form") {
    return (
      <div className="max-w-2xl mx-auto px-4 py-10">
        <h1 className="text-2xl font-bold mb-2">Deploy Your App</h1>
        <p className="text-gray-400 mb-8">
          Upload your zipped project and we'll get it live.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              App Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-awesome-app"
              className="w-full px-4 py-3 rounded-lg bg-gray-900 border border-gray-700 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none text-white placeholder-gray-500 transition-colors"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Domain Name
            </label>
            <div className="flex items-stretch">
              <input
                type="text"
                value={subdomain}
                onChange={(e) => handleSubdomainChange(e.target.value)}
                placeholder="my-cool-app"
                className="flex-1 px-4 py-3 rounded-l-lg bg-gray-900 border border-r-0 border-gray-700 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none text-white placeholder-gray-500 transition-colors font-mono"
                required
              />
              <span className="inline-flex items-center px-4 py-3 rounded-r-lg bg-gray-800 border border-l-0 border-gray-700 text-gray-400 text-sm font-mono whitespace-nowrap">
                .ai-deploy.tutaia.com
              </span>
            </div>
            {subdomain && !subdomainError && (
              <p className="mt-2 text-sm text-green-400 font-mono">
                https://{subdomain}.ai-deploy.tutaia.com
              </p>
            )}
            {subdomainError && (
              <p className="mt-2 text-sm text-red-400">{subdomainError}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Project Zip
            </label>
            <FileUpload file={file} onFile={setFile} />
          </div>

          {error && (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={!file || !name.trim() || !subdomain || !!subdomainError || submitting}
            className="w-full py-3 rounded-lg bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold text-lg"
          >
            {submitting ? (
              <span className="inline-flex items-center gap-2">
                <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                Uploading...
              </span>
            ) : (
              "🚀 Deploy"
            )}
          </button>
        </form>
      </div>
    );
  }

  if (phase === "deploying" && app) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div className="animate-spin w-12 h-12 border-3 border-primary-500 border-t-transparent rounded-full mx-auto mb-6" />
        <h2 className="text-2xl font-bold mb-2">Deploying {app.name}...</h2>
        <p className="text-gray-400 mb-6">
          We're building and deploying your app. This usually takes 2-5 minutes.
        </p>

        <div className="inline-flex items-center gap-3 px-5 py-3 rounded-xl bg-gray-900/50 border border-gray-800">
          <span className="text-sm text-gray-400">Status:</span>
          <StatusBadge status={app.status} />
        </div>

        {app.status === "failed" && (
          <div className="mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            Deployment failed. Check your project configuration and try again.
          </div>
        )}
      </div>
    );
  }

  if (phase === "done" && app) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <Confetti />
        <div className="text-5xl mb-4">🎉</div>
        <h2 className="text-3xl font-bold mb-2">Deployed!</h2>
        <p className="text-gray-400 mb-8">
          <strong className="text-white">{app.name}</strong> is now live.
        </p>

        {app.url && (
          <div className="space-y-4">
            <div className="inline-block px-6 py-3 rounded-xl bg-gray-900/50 border border-gray-800">
              <a
                href={app.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-400 hover:text-primary-300 font-mono"
              >
                {app.url}
              </a>
            </div>
            <div>
              <a
                href={app.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex px-6 py-3 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-semibold"
              >
                Open App →
              </a>
            </div>
          </div>
        )}
      </div>
    );
  }

  return null;
}
