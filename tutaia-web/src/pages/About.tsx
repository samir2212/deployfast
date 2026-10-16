import { useEffect } from "react";
import { about } from "../data/about";

const MAX_BULLETS = 4;

const card = "rounded-xl border border-gray-800 bg-gray-900/50";
const gradient =
  "bg-gradient-to-r from-primary-400 to-primary-600 bg-clip-text text-transparent";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-sm font-medium text-primary-400 uppercase tracking-wider mb-6">
      {children}
    </h2>
  );
}

function externalProps(href: string) {
  return href.startsWith("http")
    ? { target: "_blank", rel: "noopener noreferrer" }
    : {};
}

export default function About() {
  useEffect(() => {
    const previous = document.title;
    document.title = "About · Ahmed Samir · DeployFast";
    return () => {
      document.title = previous;
    };
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 pb-16">
      {/* Hero */}
      <section className="pt-16 md:pt-24 pb-8 flex flex-col sm:flex-row sm:items-center gap-6">
        <div className="w-24 h-24 shrink-0 rounded-full bg-gradient-to-br from-primary-400 to-primary-700 flex items-center justify-center text-3xl font-bold text-white shadow-lg shadow-primary-900/40">
          {about.initials}
        </div>
        <div>
          <div className="text-sm text-primary-400 font-medium mb-2">
            About me · {about.location}
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-3">
            Hi, I'm <span className={gradient}>{about.name}</span>
          </h1>
          <p className="text-gray-400 md:text-lg">{about.headline}</p>
        </div>
      </section>

      {/* Bio */}
      <section className="pb-12">
        <p className="text-gray-300 text-lg leading-relaxed">{about.bio}</p>
      </section>

      {/* Selected impact */}
      <section className="py-8">
        <SectionLabel>Selected impact</SectionLabel>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {about.impact.map((s) => (
            <div key={s.value} className={`${card} p-5`}>
              <div className="text-2xl md:text-3xl font-bold text-primary-400 mb-1">
                {s.value}
              </div>
              <div className="text-sm text-gray-400">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* What I've shipped */}
      <section className="py-8">
        <SectionLabel>What I've shipped</SectionLabel>
        <h3 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">
          {about.projectsHeading.lead}{" "}
          <span className={gradient}>{about.projectsHeading.highlight}</span>
        </h3>
        <p className="text-gray-400 mb-8">{about.projectsHeading.subtitle}</p>

        <div className="space-y-6">
          {about.projects.map((p) => (
            <article key={p.name} className={`${card} p-6 md:p-8`}>
              <div className="flex flex-col-reverse sm:flex-row sm:items-start sm:justify-between gap-3 mb-5">
                <div>
                  <div className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-2">
                    {p.eyebrow}
                  </div>
                  <h4 className="text-2xl font-bold mb-1">{p.name}</h4>
                  <p className="text-gray-300">{p.description}</p>
                </div>
                {p.status ? (
                  <span className="self-start shrink-0 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                    {p.status}
                  </span>
                ) : (
                  p.dates && (
                    <span className="self-start shrink-0 px-3 py-1 rounded-full bg-gray-800 border border-gray-700 text-gray-300 text-xs font-medium whitespace-nowrap">
                      {p.dates}
                    </span>
                  )
                )}
              </div>

              {p.stats.length > 0 && (
                <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-5">
                  {p.stats.map((s) => (
                    <div
                      key={s.label}
                      className="rounded-lg bg-gray-950/60 border border-gray-800 p-2.5 sm:p-4 min-w-0"
                    >
                      <div className="text-base sm:text-2xl font-bold text-primary-400 mb-1 break-words">
                        {s.value}
                      </div>
                      <div className="text-[11px] sm:text-xs text-gray-400 leading-snug">
                        {s.label}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <p className="text-gray-400 text-sm mb-5">{p.detail}</p>

              <div className="flex flex-wrap gap-2">
                {p.tech.map((t) => (
                  <span
                    key={t}
                    className="px-2.5 py-1 rounded-md bg-gray-800/80 text-gray-300 text-xs"
                  >
                    {t}
                  </span>
                ))}
              </div>

              {p.links.length > 0 && (
                <div className="flex flex-wrap gap-3 mt-6">
                  {p.links.map((l) => (
                    <a
                      key={l.href}
                      href={l.href}
                      {...externalProps(l.href)}
                      className={
                        l.primary
                          ? "px-5 py-2.5 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors font-semibold text-sm"
                          : "px-5 py-2.5 rounded-lg border border-gray-700 hover:border-primary-500/50 hover:bg-gray-800 transition-colors font-semibold text-sm text-gray-200"
                      }
                    >
                      {l.label}
                    </a>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      </section>

      {/* Experience */}
      <section className="py-8">
        <SectionLabel>Experience</SectionLabel>
        {about.experience.map((e) => (
          <div key={e.title}>
            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1 mb-2">
              <h3 className="text-xl font-bold">{e.title}</h3>
              <span className="text-sm text-gray-400 whitespace-nowrap">
                {e.dates} · {e.location}
              </span>
            </div>
            <p className="text-gray-400 text-sm mb-6">{e.summary}</p>

            <ol className="border-l border-gray-800 ml-1.5 space-y-8">
              {e.roles.map((r) => (
                <li key={r.company} className="relative pl-6">
                  <span className="absolute -left-[5px] top-2 w-2.5 h-2.5 rounded-full bg-primary-500" />
                  <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
                    <h4 className="font-semibold text-lg">{r.company}</h4>
                    <span className="text-sm text-gray-500 whitespace-nowrap">
                      {r.dates}
                    </span>
                  </div>
                  <div className="text-sm text-primary-300 mb-2">{r.role}</div>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-gray-400">
                    {r.bullets.slice(0, MAX_BULLETS).map((b) => (
                      <li key={b}>{b}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </section>

      {/* Skills */}
      <section className="py-8">
        <SectionLabel>Skills</SectionLabel>
        <div className="space-y-5">
          {about.skills.map((g) => (
            <div key={g.group}>
              <div className="text-sm font-semibold text-gray-200 mb-2">{g.group}</div>
              <div className="flex flex-wrap gap-2">
                {g.items.map((s) => (
                  <span
                    key={s}
                    className="px-3 py-1 rounded-full border border-primary-500/30 bg-primary-500/5 text-primary-300 text-xs"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Education */}
      <section className="py-8">
        <SectionLabel>Education</SectionLabel>
        <div className={`${card} p-6`}>
          <div className="font-semibold text-lg">
            {about.education.degree} — {about.education.school}
          </div>
          <div className="text-sm text-gray-400 mt-1">
            {about.education.dates} · {about.education.location}
          </div>
          <div className="text-sm text-gray-300 mt-3">
            {about.education.notes.join(" · ")}
          </div>
        </div>
      </section>

      {/* Get in touch */}
      <section className="py-8">
        <SectionLabel>Get in touch</SectionLabel>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {about.contacts.map((c) => (
            <a
              key={c.label}
              href={c.href}
              {...externalProps(c.href)}
              className={`${card} p-5 hover:border-primary-500/50 transition-colors`}
            >
              <div className="text-xs font-medium text-primary-400 uppercase tracking-wider mb-1">
                {c.label}
              </div>
              <div className="text-sm text-gray-200 break-all">{c.value}</div>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
