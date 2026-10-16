// All copy for the /about page. Edit here; src/pages/About.tsx only renders it.

export interface Stat {
  value: string;
  label: string;
}

export interface Project {
  name: string;
  eyebrow: string;
  description: string;
  /** Date range shown in the pill; omitted when `status` is set. */
  dates?: string;
  /** Status pill shown instead of dates (e.g. "Public beta"). */
  status?: string;
  stats: Stat[];
  detail: string;
  tech: string[];
  links: { label: string; href: string; primary?: boolean }[];
}

export interface Role {
  company: string;
  role: string;
  dates: string;
  /** Full list from the CV; the page shows at most 4. */
  bullets: string[];
}

export interface Experience {
  title: string;
  dates: string;
  location: string;
  summary: string;
  roles: Role[];
}

export interface SkillGroup {
  group: string;
  items: string[];
}

export interface Education {
  degree: string;
  school: string;
  dates: string;
  location: string;
  notes: string[];
}

export interface Contact {
  label: string;
  value: string;
  href: string;
}

export interface AboutData {
  name: string;
  initials: string;
  headline: string;
  location: string;
  bio: string;
  impact: Stat[];
  projectsHeading: { lead: string; highlight: string; subtitle: string };
  projects: Project[];
  experience: Experience[];
  skills: SkillGroup[];
  education: Education;
  contacts: Contact[];
}

export const about: AboutData = {
  name: "Ahmed Samir",
  initials: "AS",
  headline:
    "Fractional Platform Lead · AWS Cloud & Serverless Architect · Cost Optimization",
  location: "London, UK · Remote",
  bio: "I help early-stage startups turn cloud and AI into business results: lower cloud bills, faster delivery, and platforms that are ready for investors and enterprise customers. I have cut cloud costs by 75–78% on two production platforms, led a Series A technical due diligence, and built AI assistants and agents that replaced manual work in student support, team onboarding and sales.",

  impact: [
    { value: "75–78%", label: "AWS cost cut on two platforms + hundreds of accounts" },
    { value: "200K+", label: "students on a serverless cybersecurity EdTech platform" },
    { value: "1.3%", label: "of German power: energy trading platform, cloud lead" },
    { value: "2 min → 3 s", label: "lab launch time for students" },
    { value: "Series A", label: "led the cloud & technical due diligence" },
    { value: "SOC 2", label: "aligned security: Security Hub, GuardDuty, IAM Access Analyzer" },
  ],

  projectsHeading: {
    lead: "Always building startups",
    highlight: "on the cloud",
    subtitle: "Platforms I've built and run for years, from day one to real scale.",
  },

  projects: [
    {
      name: "Suena Energy",
      eyebrow: "Energy trading · Series A",
      description: "Cloud lead for a platform trading 1.3% of Germany's electricity.",
      dates: "Sep 2024 – Present",
      stats: [
        { value: "78%", label: "infrastructure cost cut" },
        { value: "Series A", label: "led cloud due diligence" },
        { value: "300+", label: "Lambdas refactored" },
      ],
      detail:
        "Replaced Confluent Kafka with an in-house event-driven scheduler, split CI/CD into IaC/app/Lambda pipelines, and built the data lake and the observability stack.",
      tech: ["AWS Lambda", "Terraform", "DynamoDB · GraphQL", "Glue · Athena", "Grafana · Sentry"],
      links: [],
    },
    {
      name: "Security Blue Team",
      eyebrow: "Cybersecurity EdTech · Founding engineer",
      description: "The fully serverless platform behind the BTL1 & BTL2 courses.",
      dates: "Oct 2022 – Apr 2025",
      stats: [
        { value: "200K+", label: "students served" },
        { value: "2 min → 3 s", label: "lab launch time" },
        { value: "75%", label: "AWS cost cut" },
      ],
      detail:
        "Designed multi-region failover and SOC 2-aligned security across accounts, and built exam activity monitoring and an AI tutor on the OpenAI Assistants API.",
      tech: ["Serverless", "EventBridge · SNS", "Global Accelerator", "Terraform · Boto3", "Security Hub · GuardDuty"],
      links: [],
    },
    {
      name: "DeployFast",
      eyebrow: "My own product · Tutaia",
      description: "Deploy your vibe-coded app in 60 seconds.",
      status: "Public beta",
      stats: [],
      detail:
        "Zip upload → Nixpacks build → live HTTPS URL on AWS ECS Fargate. Designed, built and operated end to end.",
      tech: ["React", "FastAPI", "PostgreSQL", "AWS ECS · CodeBuild", "Terraform", "Stripe · Clerk"],
      links: [
        { label: "Try it live →", href: "https://deployfast.tutaia.com", primary: true },
        { label: "View on GitHub", href: "https://github.com/samir2212/deployfast" },
      ],
    },
  ],

  experience: [
    {
      title: "Independent Cloud Consultant / Fractional Platform Lead",
      dates: "Oct 2021 – Present",
      location: "Remote",
      summary:
        "Long-term, part-time and project-based engagements with startups and AWS partners, often running in parallel.",
      roles: [
        {
          company: "Suena Energy",
          role: "Senior Platform Engineer, Energy Trading",
          dates: "Sep 2024 – Present",
          bullets: [
            "Lead cloud development for an energy trading platform serving 1.3% of Germany's electricity market.",
            "Led the Series A cloud due diligence (architecture, DR, performance benchmarks, deployment workflows, security).",
            "Cut infrastructure costs by 78%.",
            "Replaced Confluent Kafka with an in-house event-driven scheduler.",
            "Refactored 300+ AWS Lambdas.",
            "Split a monolithic CI/CD into IaC / app / Lambda pipelines.",
            "Terraform IaC across multiple AWS accounts.",
            "Built an S3/Glue/Lake Formation/Athena data lake.",
            "Built observability (CloudWatch, Teams/email alerts, Sentry, an internal Grafana Dashboard Manager across 3 environments).",
            "Ran AI workshops and built a GPT-powered onboarding assistant.",
          ],
        },
        {
          company: "Security Blue Team",
          role: "Founding Platform Engineer, EdTech",
          dates: "Oct 2022 – Apr 2025",
          bullets: [
            "Built the fully serverless platform behind the BTL1 and BTL2 courses, serving 200K+ students.",
            "Cut AWS costs by 75% and improved latency with Global Accelerator.",
            "Reduced lab start time from 2 minutes to 3 seconds.",
            "Designed multi-region failover.",
            "Built cloud lab infrastructure with Terraform + Boto3 across accounts.",
            "Implemented SOC 2-aligned security (Security Hub, GuardDuty, IAM Access Analyzer).",
            "Built serverless exam activity monitoring.",
            "Automated AMI size reduction with Step Functions + SSM.",
            "Built an AI tutor on the OpenAI Assistants API.",
            "Mentored engineers.",
          ],
        },
        {
          company: "Cloudvisor",
          role: "Founding DevOps Engineer, AWS Partner",
          dates: "Oct 2021 – Apr 2025",
          bullets: [
            "Built startup infrastructure from scratch with Terraform (blockchain, fintech, e-commerce, food tech).",
            "Ran cost reduction reviews for hundreds of customer AWS accounts.",
            "Migrated the billing app from EC2 to ECS.",
            "Built CI/CD on GitLab, GitHub and Bitbucket.",
            "Launched new revenue streams (migrations, training, proactive support).",
            "Earned GCP Associate Cloud Engineer, helping Cloudvisor become a GCP partner.",
            "Raised team delivery rate to 85% with Scrum.",
          ],
        },
        {
          company: "Serverless Guru",
          role: "Senior Cloud Sales Engineer, AWS Partner",
          dates: "May 2024 – Aug 2025",
          bullets: [
            "Worked with the CEO and CTO on sales strategy and go-to-market.",
            "Built the sales function (processes, CRM, playbooks).",
            "Engineered AI agents that automated lead generation, email campaigns and follow-ups (thousands of qualified leads, no extra headcount).",
            "Represented the company at AWS re:Invent and opened conversations with Hilton and Marriott.",
          ],
        },
      ],
    },
  ],

  skills: [
    {
      group: "Cloud",
      items: [
        "AWS (Lambda, ECS, EC2, RDS, S3, DynamoDB, EventBridge, SQS, SNS, Step Functions, Glue, Athena, Lake Formation, Global Accelerator)",
        "GCP",
      ],
    },
    {
      group: "IaC & CI/CD",
      items: ["Terraform", "Boto3", "GitLab CI/CD", "GitHub", "Bitbucket", "Docker", "YAML"],
    },
    { group: "Observability", items: ["CloudWatch", "Grafana", "Sentry"] },
    {
      group: "Security",
      items: ["Security Hub", "GuardDuty", "IAM Access Analyzer", "SOC 2-aligned controls", "Multi-account setup"],
    },
    {
      group: "AI",
      items: ["OpenAI API and Assistants", "GPT-based internal tools", "AI agents for automation"],
    },
    { group: "Languages", items: ["Python", "Java", "Linux"] },
    {
      group: "Ways of working",
      items: ["Solution architecture", "Startups", "Product management", "Scrum", "Agile"],
    },
  ],

  education: {
    degree: "BSc Communications Engineering",
    school: "The German University in Cairo",
    dates: "2014 – 2019",
    location: "Cairo, Egypt",
    notes: ["Grade: Very Good", "Bachelor thesis: Excellent", "50% partial scholarship"],
  },

  contacts: [
    { label: "Email", value: "ahmedsamir1922@gmail.com", href: "mailto:ahmedsamir1922@gmail.com" },
    { label: "LinkedIn", value: "linkedin.com/in/ahmedsamir22", href: "https://linkedin.com/in/ahmedsamir22" },
    { label: "GitHub", value: "github.com/samir2212", href: "https://github.com/samir2212" },
    { label: "GitLab", value: "gitlab.com/samir2279", href: "https://gitlab.com/samir2279" },
  ],
};
