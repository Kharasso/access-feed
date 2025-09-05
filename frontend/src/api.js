// // api.js
// const DEFAULT_API = `${location.protocol}//${location.hostname}:8080`;
// export const API =
//   (import.meta?.env?.VITE_API_BASE && import.meta.env.VITE_API_BASE.trim()) ||
//   DEFAULT_API;

const getDefaultApi = () => {
  // In production, don't append :8080
  if (import.meta.env.PROD) {
    // This won't work, but at least won't hang
    console.error('API base URL not configured. Set VITE_API_BASE in environment variables.');
    return `${location.protocol}//${location.hostname}`;
  }
  // In development, use localhost:8080
  return `${location.protocol}//${location.hostname}:8080`;
};

export const API = 
  (import.meta?.env?.VITE_API_BASE && import.meta.env.VITE_API_BASE.trim()) ||
  getDefaultApi();

console.log('API Base URL:', API); 

export async function getFeed(limit = 50) {
  const url = `${API}/feed?limit=${limit}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`GET /feed failed: ${r.status} ${r.statusText}`);
  return r.json();
}

export async function setPreferences(prefs) {
  const r = await fetch(`${API}/preferences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prefs),
  });
  if (!r.ok) throw new Error(`POST /preferences failed: ${r.status}`);
  return r.json();
}


