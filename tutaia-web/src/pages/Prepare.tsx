import { useState } from "react";
import { Link } from "react-router-dom";

const PROMPT = `Before I upload this project to Tutaia for deployment, please help me run through this pre-deploy checklist:

1. **requirements.txt / package.json** — Make sure the dependency file exists at the project root and includes ALL dependencies needed to run the app (not just dev deps).

2. **Port binding** — The app must read the PORT environment variable and bind to it. For example:
   - Python Flask: \`app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))\`
   - Node/Express: \`app.listen(process.env.PORT || 3000)\`
   - Streamlit: Already handled by Tutaia's build system.

3. **Database initialization** — If the app uses SQLite or any local database, make sure it creates/migrates the database on startup (not in a separate script).

4. **No hardcoded secrets** — Scan for any API keys, passwords, or tokens hardcoded in the source. They should be read from environment variables instead.

5. **Clean zip** — Generate a clean zip of the project root folder. Exclude: \`.git/\`, \`node_modules/\`, \`__pycache__/\`, \`.env\`, \`venv/\`, \`.venv/\`, any large binary files not needed at runtime.

6. **Entry point** — Confirm the app has a clear entry point (e.g., \`app.py\`, \`main.py\`, \`server.js\`, or a \`start\` script in package.json).

Please check each item, fix any issues, and then generate the zip file for me.`;

export default function Prepare() {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(PROMPT).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold mb-2">Prepare Your App</h1>
      <p className="text-gray-400 mb-8">
        Copy this prompt and paste it into Claude Code (or your AI tool of
        choice) to make sure your project is ready for deployment.
      </p>

      <div className="relative rounded-xl border border-gray-800 bg-gray-900/50 p-6 mb-6">
        <pre className="whitespace-pre-wrap text-sm text-gray-300 font-mono leading-relaxed max-h-96 overflow-y-auto">
          {PROMPT}
        </pre>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <button
          onClick={handleCopy}
          className="flex-1 px-6 py-3 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-semibold text-center"
        >
          {copied ? "✓ Copied!" : "📋 Copy Prompt"}
        </button>

        <Link
          to="/deploy"
          className="flex-1 px-6 py-3 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors font-semibold text-center"
        >
          I've run it, ready to deploy →
        </Link>
      </div>
    </div>
  );
}
