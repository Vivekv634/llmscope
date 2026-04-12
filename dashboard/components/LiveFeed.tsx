"use client";

import { useTokenStream } from "@/hooks/useTokenStream";

interface LiveFeedProps {
  runId: string;
  staticText: string | null;
}

export function LiveFeed({ runId, staticText }: LiveFeedProps) {
  const { tokens, done } = useTokenStream(runId);

  if (staticText !== null && tokens.length === 0) {
    return (
      <pre className="text-sm whitespace-pre-wrap leading-relaxed text-gray-700">
        {staticText}
      </pre>
    );
  }

  const liveText = tokens.map((t) => t.text).join("");

  return (
    <div>
      <pre className="text-sm whitespace-pre-wrap leading-relaxed text-gray-700">
        {liveText}
        {!done && (
          <span className="inline-block w-1.5 h-4 bg-indigo-500 ml-0.5 animate-pulse" />
        )}
      </pre>
      {done && (
        <p className="text-xs text-gray-400 mt-2">Stream complete</p>
      )}
    </div>
  );
}
