import { getSessionTimeline } from "@/lib/api/sessions";
import { orNotFound } from "@/lib/api/client";
import { EmptyState } from "@/components/EmptyState";
import { formatTimestamp } from "@/lib/format";
import type { MessageTimelineEntry, ToolCallTimelineEntry } from "@/lib/api/types";

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

function ToolCallCard({ toolCall }: { toolCall: ToolCallTimelineEntry }) {
  return (
    <div className="ml-4 mt-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs">
      <div className="font-mono font-medium text-slate-700">
        {toolCall.tool_name}(
        {JSON.stringify(toolCall.arguments)})
      </div>
      {toolCall.result ? (
        <div
          className={`mt-1 font-mono ${toolCall.result.is_error ? "text-red-700" : "text-slate-600"}`}
        >
          {toolCall.result.is_error ? "error: " : "result: "}
          {JSON.stringify(toolCall.result.output)}
        </div>
      ) : (
        <div className="mt-1 text-slate-400">Awaiting result…</div>
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
    <ol className="space-y-4">
      {timeline.messages.map((message) => (
        <li
          key={message.id}
          className={`rounded-lg border px-4 py-3 ${roleColorClasses[message.role]}`}
        >
          <div className="flex items-center justify-between gap-4 text-xs text-slate-500">
            <span className="font-medium uppercase tracking-wide">
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
        </li>
      ))}
    </ol>
  );
}
