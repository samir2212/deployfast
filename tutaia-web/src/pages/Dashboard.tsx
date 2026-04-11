import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { type App, type SubscriptionStatus, listApps, getSubscriptionStatus, deleteApp } from "../api";
import StatusBadge from "../components/StatusBadge";

export default function Dashboard() {
  const { getToken } = useAuth();
  const [apps, setApps] = useState<App[]>([]);
  const [sub, setSub] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const token = await getToken();
        if (!token) throw new Error("Not authenticated");
        const [data, status] = await Promise.all([
          listApps(token),
          getSubscriptionStatus(token).catch(() => null),
        ]);
        if (!cancelled) {
          setApps(data);
          setSub(status);
        }
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load apps");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto" />
        <p className="text-gray-400 mt-4">Loading your apps...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="text-center py-16 rounded-xl border border-red-500/20 bg-red-500/5">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold mb-2">Could not load apps</h2>
          <p className="text-gray-400 mb-4 text-sm max-w-md mx-auto">
            {error.includes("401")
              ? "Authentication failed. The API could not verify your session. This may be a backend configuration issue."
              : error}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg border border-gray-700 hover:border-gray-600 text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  async function handleDelete(appId: string) {
    if (!confirm("Are you sure you want to delete this app? This cannot be undone.")) return;
    setDeleting(appId);
    try {
      const token = await getToken();
      if (!token) return;
      await deleteApp(appId, token);
      setApps((prev) => prev.filter((a) => a.id !== appId));
    } catch {
      alert("Failed to delete app.");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      {sub && !sub.active && (
        <div className="mb-6 p-4 rounded-xl border border-yellow-500/20 bg-yellow-500/5 flex items-center justify-between">
          <p className="text-yellow-300 text-sm">
            You need an active plan to deploy apps.
          </p>
          <Link
            to="/pricing"
            className="shrink-0 ml-4 px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-sm font-medium transition-colors"
          >
            Choose a plan →
          </Link>
        </div>
      )}

      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Your Apps</h1>
        <Link
          to="/prepare"
          className="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors text-sm font-medium"
        >
          + Deploy New App
        </Link>
      </div>

      {apps.length === 0 ? (
        <div className="text-center py-20 rounded-xl border border-gray-800 bg-gray-900/50">
          <div className="text-4xl mb-4">🚀</div>
          <h2 className="text-xl font-semibold mb-2">No apps yet</h2>
          <p className="text-gray-400 mb-6">
            Deploy your first app and it will appear here.
          </p>
          <Link
            to="/prepare"
            className="inline-flex px-5 py-2.5 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-medium"
          >
            Deploy Your First App
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {apps.map((app) => (
            <div
              key={app.id}
              className="flex items-center justify-between p-5 rounded-xl border border-gray-800 bg-gray-900/50 hover:border-gray-700 transition-colors"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="font-semibold truncate">{app.name}</h3>
                  <StatusBadge status={app.status} />
                </div>
                {app.url && (
                  <a
                    href={app.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary-400 hover:text-primary-300 truncate block"
                  >
                    {app.url}
                  </a>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Deployed {new Date(app.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-4">
                {app.url && app.status === "running" && (
                  <a
                    href={app.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 rounded-lg border border-gray-700 hover:border-gray-600 text-sm transition-colors"
                  >
                    Open →
                  </a>
                )}
                <button
                  onClick={() => handleDelete(app.id)}
                  disabled={deleting === app.id}
                  className="px-3 py-2 rounded-lg border border-gray-700 hover:border-red-500/50 hover:text-red-400 text-gray-500 text-sm transition-colors disabled:opacity-50"
                >
                  {deleting === app.id ? "..." : "Delete"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
