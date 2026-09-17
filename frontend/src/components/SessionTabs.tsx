"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { segment: "", label: "Timeline" },
  { segment: "health", label: "Context Health" },
  { segment: "events", label: "Detection Events" },
  { segment: "hallucinations", label: "Hallucination Analysis" },
] as const;

export function SessionTabs({ sessionId }: { sessionId: string }) {
  const pathname = usePathname();
  const basePath = `/sessions/${sessionId}`;

  return (
    <nav className="flex gap-1 border-b border-slate-200">
      {TABS.map((tab) => {
        const href = tab.segment ? `${basePath}/${tab.segment}` : basePath;
        const isActive =
          tab.segment === ""
            ? pathname === basePath
            : pathname.startsWith(href);
        return (
          <Link
            key={tab.segment || "timeline"}
            href={href}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              isActive
                ? "border-slate-900 text-slate-900"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
