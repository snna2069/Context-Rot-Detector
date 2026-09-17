"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ActivityIcon,
  ChatBubbleIcon,
  ListIcon,
  ShieldIcon,
} from "@/components/icons";

const TABS = [
  { segment: "", label: "Timeline", icon: ChatBubbleIcon },
  { segment: "health", label: "Context Health", icon: ActivityIcon },
  { segment: "events", label: "Detection Events", icon: ListIcon },
  { segment: "hallucinations", label: "Hallucination Analysis", icon: ShieldIcon },
] as const;

export function SessionTabs({ sessionId }: { sessionId: string }) {
  const pathname = usePathname();
  const basePath = `/sessions/${sessionId}`;

  return (
    <nav className="flex flex-wrap gap-1 rounded-lg bg-slate-100/80 p-1 text-sm">
      {TABS.map((tab) => {
        const href = tab.segment ? `${basePath}/${tab.segment}` : basePath;
        const isActive =
          tab.segment === ""
            ? pathname === basePath
            : pathname.startsWith(href);
        const Icon = tab.icon;
        return (
          <Link
            key={tab.segment || "timeline"}
            href={href}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all ${
              isActive
                ? "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200"
                : "text-slate-500 hover:bg-white/60 hover:text-slate-800"
            }`}
          >
            <Icon className={`h-4 w-4 ${isActive ? "text-indigo-600" : "text-slate-400"}`} />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
