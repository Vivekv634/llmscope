"use client";

import { useEffect, useRef, useState } from "react";
import { wsUrl } from "@/lib/api";
import type { WsEvent, WsTokenEvent } from "@/types/api";

export interface TokenStreamState {
  tokens: WsTokenEvent[];
  done: boolean;
}

export function useTokenStream(runId: string): TokenStreamState {
  const [tokens, setTokens] = useState<WsTokenEvent[]>([]);
  const [done, setDone] = useState<boolean>(false);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(wsUrl(runId));

    ws.current.onmessage = (e: MessageEvent<string>) => {
      const event = JSON.parse(e.data) as WsEvent;
      if (event.type === "token") {
        setTokens((prev) => [...prev, event]);
      } else if (event.type === "done") {
        setDone(true);
        ws.current?.close();
      }
    };

    ws.current.onerror = () => {
      ws.current?.close();
    };

    return () => {
      ws.current?.close();
    };
  }, [runId]);

  return { tokens, done };
}
