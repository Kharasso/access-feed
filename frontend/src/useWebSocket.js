import { useEffect, useRef } from "react";
import { API } from "./api";

function wsUrlFromApi(apiBase) {
  try {
    const u = new URL(apiBase);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    u.pathname = "/ws";
    u.search = "";
    u.hash = "";
    return u.toString();
  } catch {
    const proto = location.protocol === "https:" ? "wss://" : "ws://";
    return `${proto}${location.hostname}:8080/ws`;
  }
}

export function useWS(onMsg) {
  const ref = useRef(null);
  useEffect(() => {
    const url = wsUrlFromApi(API);
    const ws = new WebSocket(url);
    ref.current = ws;

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
       
        if (msg && msg.kind === "deal_item" && msg.data) onMsg(msg);
      } catch (e) {
        console.error("WS parse error", e);
      }
    };
    ws.onerror = (e) => console.error("WS error", e);

    return () => ws.close();
  }, [onMsg]);

  return ref;
}
