// // api.js
// const DEFAULT_API = `${location.protocol}//${location.hostname}:8080`;
// export const API =
//   (import.meta?.env?.VITE_API_BASE && import.meta.env.VITE_API_BASE.trim()) ||
//   DEFAULT_API;

// export async function getFeed(limit = 50) {
//   const url = `${API}/feed?limit=${limit}`;
//   const r = await fetch(url);
//   if (!r.ok) throw new Error(`GET /feed failed: ${r.status} ${r.statusText}`);
//   return r.json();
// }

// export async function setPreferences(prefs) {
//   const r = await fetch(`${API}/preferences`, {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify(prefs),
//   });
//   if (!r.ok) throw new Error(`POST /preferences failed: ${r.status}`);
//   return r.json();
// }
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function getFeed() {
  const r = await fetch(`${API_BASE}/feed`);
  return r.json();
}

export async function setPreferences(prefs) {
  const r = await fetch(`${API_BASE}/preferences`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(prefs),
  });
  return r.json();
}