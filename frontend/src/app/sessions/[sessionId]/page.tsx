import { getSessionTimeline } from "@/lib/api/sessions";
import { orNotFound } from "@/lib/api/client";
import { EmptyState } from "@/components/EmptyState";
import { formatTimestamp } from "@/lib/format";
import { CpuIcon, TerminalIcon, UserIcon, WrenchIcon } from "@/components/icons";
import type { MessageTimelineEntry, ToolCallTimelineEntry } from "@/lib/api/types";
import type { ComponentType, SVGProps } from "react";

const roleLabels: Record<MessageTimelineEntry["role"], string> = {
  system: "System",
  developer: "Developer",
  user: "User",
  assistant: "Assistant",
  tool: "Tool",
};

const roleColorClasses: Record<MessageTimelineEntry["role"], string> = {
  system: "border-slate-300 bg-slate-50",
  developer: "border-purple-200 bg-purple-50",
  user: "border-blue-200 bg-blue-50",
  assistant: "border-emerald-200 bg-emerald-50",
  tool: "border-amber-200 bg-amber-50",
};

const roleAvatarClasses: Record<MessageTimelineEntry["role"], string> = {
  system: "bg-slate-500",
  developer: "bg-purple-500",
  user: "bg-blue-500",
  assistant: "bg-emerald-500",
  tool: "bg-amber-500",
};

const roleIcons: Record<MessageTimelineEntry["role"], ComponentType<SVGProps<SVGSVGElement>>> = {
  system: TerminalIcon,
  developer: TerminalIcon,
  user: UserIcon,
  assistant: CpuIcon,
  tool: WrenchIcon,
};

function ToolCallCard({ toolCall }: { toolCall: ToolCallTimelineEntry }) {
  return (
    <div className="ml-1 mt-2 rounded-lg border border-slate-200 bg-slate-900/95 px-3 py-2 font-mono text-xs text-slate-100 shadow-inner">
      <div className="flex items-center gap-1.5 text-emerald-300">
        <WrenchIcon className="h-3.5 w-3.5" />
        <span className="font-medium">
          {toolCall.tool_name}({JSON.stringify(toolCall.arguments)})
        </span>
      </div>
      {toolCall.result ? (
        <div
          className={`mt-1.5 border-t border-slate-700/60 pt-1.5 ${toolCall.result.is_error ? "text-red-300" : "text-slate-300"}`}
        >
          {toolCall.result.is_error ? "✗ error: " : "✓ result: "}
          {JSON.stringify(toolCall.result.output)}
        </div>
      ) : (
        <div className="mt-1.5 text-slate-500">Awaiting result…</div>
      )}
    </div>
  );
}

export default async function SessionTimelinePage({
  params,
}: PageProps<"/sessions/[sessionId]">) {
  const { sessionId } = await params;
  const timeline = await orNotFound(getSessionTimeline(sessionId));

  if (timeline.messages.length === 0) {
    return (
      <EmptyState
        title="No messages yet"
        description="Messages will appear here once this session has ingested data."
      />
    );
  }

  return (
    <ol className="relative space-y-4 before:absolute before:left-[19px] before:top-2 before:h-[calc(100%-1rem)] before:w-px before:bg-slate-200 sm:before:left-[19px]">
      {timeline.messages.map((message) => {
        const Icon = roleIcons[message.role];
        return (
          <li key={message.id} className="relative flex gap-3 pl-0">
            <span
              className={`relative z-10 mt-1 flex h-8 w-8 flex-none items-center justify-center rounded-full text-white shadow-sm ${roleAvatarClasses[message.role]}`}
            >
              <Icon className="h-4 w-4" strokeWidth={1.8} />
            </span>
            <div
              className={`flex-1 rounded-lg border px-4 py-3 shadow-sm transition hover:shadow ${roleColorClasses[message.role]}`}
            >
              <div className="flex items-center justify-between gap-4 text-xs text-slate-500">
                <span className="font-semibold uppercase tracking-wide">
                  {roleLabels[message.role]}
                </span>
                <span>
                  #{message.sequence_number} · {formatTimestamp(message.created_at)}
                </span>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-800">
                {message.content}
              </p>
              {message.tool_calls.map((toolCall) => (
                <ToolCallCard key={toolCall.id} toolCall={toolCall} />
              ))}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
