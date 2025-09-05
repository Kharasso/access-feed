import { useEffect, useRef } from "react";
import { API } from "./api";

// function wsUrlFromApi(apiBase) {
//   try {
//     const u = new URL(apiBase);
//     u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
//     u.pathname = "/ws";
//     u.search = "";
//     u.hash = "";
//     return u.toString();
//   } catch {
//     const proto = location.protocol === "https:" ? "wss://" : "ws://";
//     return `${proto}${location.hostname}:8080/ws`;
//   }
// }
export function wsUrlFromApi(apiBase) {
  // 1) Explicit override (recommended for Vercel: set VITE_WS_URL in Project → Settings → Environment Variables)
  const envWs = import.meta.env?.VITE_WS_URL;
  if (envWs) return envWs;

  // 2) Derive from API base (e.g., https://your-backend.onrender.com -> wss://your-backend.onrender.com/ws)
  try {
    const u = new URL(apiBase);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    // ensure single /ws regardless of existing path
    u.pathname = (u.pathname.replace(/\/+$/, "") + "/ws").replace(/\/{2,}/g, "/");
    u.search = "";
    u.hash = "";
    return u.toString();
  } catch {
    // 3) Last-resort: same host as current page (works if backend is reverse-proxied under same domain)
    const { protocol, host } = window.location;
    const wsProto = protocol === "https:" ? "wss:" : "ws:";
    console.log(`${wsProto}//${host}/ws`);
    return `${wsProto}//${host}/ws`;
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
