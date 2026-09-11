import { getHealth } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  const health = await getHealth();

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-8 px-6 py-16">
      <section className="space-y-4">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Context Rot Detector
        </p>
        <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-6xl">
          Evidence before conclusions.
        </h1>
        <p className="max-w-2xl text-lg leading-8 text-slate-600">
          The foundation for monitoring long-running AI-agent sessions is ready.
          Session ingestion and analysis will be added in later phases.
        </p>
      </section>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <h2 className="font-medium text-slate-900">Backend status</h2>
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
            {health.status}
          </span>
        </div>
      </section>
    </main>
  );
}
