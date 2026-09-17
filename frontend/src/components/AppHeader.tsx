import Link from "next/link";
import { SparkleIcon } from "@/components/icons";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-3.5">
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-emerald-500 text-white shadow-sm transition-transform group-hover:scale-105">
            <SparkleIcon className="h-5 w-5" strokeWidth={1.8} />
          </span>
          <span className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight text-slate-900">
              Context Rot Detector
            </span>
            <span className="text-[11px] text-slate-400">
              Evidence before conclusions
            </span>
          </span>
        </Link>
      </div>
    </header>
  );
}
