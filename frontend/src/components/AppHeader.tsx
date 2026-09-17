import Link from "next/link";

export function AppHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex flex-col">
          <span className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            Context Rot Detector
          </span>
          <span className="text-xs text-slate-400">
            Evidence before conclusions
          </span>
        </Link>
      </div>
    </header>
  );
}
