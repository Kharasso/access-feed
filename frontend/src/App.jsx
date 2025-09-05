import { useEffect, useMemo, useState, useCallback } from "react";
import { getFeed } from "./api";
import { useWS } from "./useWebSocket";
import Card from "./components/Card";
import Filters from "./components/Filters";

export default function App() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [etype, setEtype] = useState("All");
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log("App mounted");
    getFeed()
      .then(setItems)
      .catch((e) => {
        console.error(e);
        setError(e.message || "Failed to load feed");
      });
  }, []);

  const onMsg = useCallback((env) => {
  
    if (!env || env.kind !== "deal_item" || !env.data) return;
    setItems((prev) => {
      const exists = prev.find((x) => x.id === env.data.id);
      if (exists) return prev;
      return [env.data, ...prev].slice(0, 200);
    });
  }, []);

  useWS(onMsg);

  const filtered = useMemo(() => {
    return items
      .filter((i) => etype === "All" || i.event_type === etype)
      .filter(
        (i) =>
          q === "" ||
          (i.title + " " + i.summary).toLowerCase().includes(q.toLowerCase())
      )
      .sort((a, b) => b.score - a.score);
  }, [items, q, etype]);

  return (
    <div className="mx-auto max-w-5xl p-4 space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Deal Feed</h1>
        <div className="flex gap-2">
          <input
            placeholder="Search…"
            className="rounded-xl border p-2"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <select
            className="rounded-xl border p-2"
            value={etype}
            onChange={(e) => setEtype(e.target.value)}
          >
            {["All", "M&A", "Financing", "Exit", "Partnership", "Other"].map(
              (x) => (
                <option key={x}>{x}</option>
              )
            )}
          </select>
        </div>
      </header>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <Filters onApplied={() => getFeed().then(setItems).catch(console.error)} />

      {filtered.length === 0 ? (
        <div className="rounded-xl border p-6 text-sm text-gray-600">
          No items yet. If this is a fresh start, give the backend a minute to
          poll RSS. Open DevTools → Console for any errors.
        </div>
      ) : (
        <div className="grid gap-3">
          {filtered.map((itm) => itm && itm.id && <Card key={itm.id} item={itm} />)}
        </div>
      )}
    </div>
  );
}
