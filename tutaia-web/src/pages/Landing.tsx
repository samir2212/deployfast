import { Link } from "react-router-dom";
import { SignedIn, SignedOut } from "@clerk/clerk-react";

export default function Landing() {
  return (
    <div className="max-w-6xl mx-auto px-4">
      {/* Hero */}
      <section className="pt-24 pb-16 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-sm font-medium mb-8">
          <span>🚀</span> Now in public beta
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
          Deploy your{" "}
          <span className="bg-gradient-to-r from-primary-400 to-primary-600 bg-clip-text text-transparent">
            vibe-coded app
          </span>
          <br />
          in 60 seconds
        </h1>

        <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-10">
          Zip your project, upload it, get a live HTTPS URL. No Docker, no CI/CD
          pipeline, no config files. Just ship it.
        </p>

        <div className="flex gap-4 justify-center">
          <SignedOut>
            <Link
              to="/pricing"
              className="px-6 py-3 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-semibold text-lg"
            >
              Deploy Your First App
            </Link>
          </SignedOut>
          <SignedIn>
            <Link
              to="/prepare"
              className="px-6 py-3 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-semibold text-lg"
            >
              Deploy Now
            </Link>
          </SignedIn>
        </div>
      </section>

      {/* Before / After */}
      <section className="py-16">
        <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-8">
            <div className="text-sm font-medium text-red-400 mb-4 uppercase tracking-wider">
              Before
            </div>
            <div className="font-mono text-gray-300 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-gray-600">$</span> python app.py
              </div>
              <div className="text-gray-500">
                * Running on http://localhost:5000
              </div>
              <div className="text-gray-600 text-sm mt-4">
                Stuck on your machine. Nobody can see it. 😞
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-primary-500/30 bg-primary-500/5 p-8">
            <div className="text-sm font-medium text-green-400 mb-4 uppercase tracking-wider">
              After Deployfast
            </div>
            <div className="font-mono text-gray-300 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-green-400">✓</span> Deployed successfully
              </div>
              <div className="text-primary-400">
                https://my-app.tutaia.com
              </div>
              <div className="text-gray-400 text-sm mt-4">
                Live URL. Share it with anyone. 🎉
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16">
        <h2 className="text-3xl font-bold text-center mb-12">How it works</h2>
        <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          {[
            {
              step: "1",
              title: "Prepare",
              desc: "Run our pre-deploy checklist prompt in your AI coding tool to make sure your app is deployment-ready.",
            },
            {
              step: "2",
              title: "Upload",
              desc: "Zip your project and drag it onto Tutaia. Give it a name, hit deploy.",
            },
            {
              step: "3",
              title: "Ship",
              desc: "We build, containerize, and deploy your app. You get a live HTTPS URL in minutes.",
            },
          ].map((item) => (
            <div
              key={item.step}
              className="text-center p-6 rounded-xl bg-gray-900/50 border border-gray-800"
            >
              <div className="w-10 h-10 rounded-full bg-primary-600 text-white font-bold flex items-center justify-center mx-auto mb-4">
                {item.step}
              </div>
              <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
              <p className="text-gray-400 text-sm">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-10 mt-16 flex flex-col items-center gap-4">
        <a
          href="https://deployfast.tutaia.com"
          className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full bg-gray-900 border border-gray-700 hover:border-primary-500/50 hover:bg-gray-800 transition-all shadow-lg"
        >
          <span className="text-sm text-gray-400">Deployed with</span>
          <img src="/logo.png" alt="Tutaia" className="w-5 h-5 rounded" />
          <span className="text-sm font-bold text-white">Deployfast</span>
        </a>
      </footer>
    </div>
  );
}
