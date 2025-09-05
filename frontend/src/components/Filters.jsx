import { useState } from "react";
import { setPreferences } from "../api";

export default function Filters({ onApplied }) {
  const [keywords, setKeywords] = useState("CapEx, report");
  const [firms, setFirms] = useState("KKR, Blackstone");
  const [sectors, setSectors] = useState("Industrial, Healthcare");
  const [geos, setGeos] = useState("US, Europe");

  const [saving, setSaving] = useState(false);

  async function apply() {
    try {
      setSaving(true);
      const prefs = {
        user_id: "demo",
        keywords: keywords.split(",").map((s) => s.trim()).filter(Boolean),
        firms: firms.split(",").map((s) => s.trim()).filter(Boolean),
        sectors: sectors.split(",").map((s) => s.trim()).filter(Boolean),
        geos: geos.split(",").map((s) => s.trim()).filter(Boolean),
      };
      await setPreferences(prefs);
      onApplied?.(prefs);
    } catch (e) {
      console.error(e);
    } finally {
      // brief delay so user sees the "clicked" state
      setTimeout(() => setSaving(false), 100);
    }
  }

  return (
    <div className="rounded-2xl border p-4 shadow-sm grid gap-2 md:grid-cols-4">
      <div>
        <label className="text-xs text-gray-500">Keywords</label>
        <input
          className="w-full rounded-xl border p-2"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs text-gray-500">Firms</label>
        <input
          className="w-full rounded-xl border p-2"
          value={firms}
          onChange={(e) => setFirms(e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs text-gray-500">Sectors</label>
        <input
          className="w-full rounded-xl border p-2"
          value={sectors}
          onChange={(e) => setSectors(e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs text-gray-500">Geographies</label>
        <input
          className="w-full rounded-xl border p-2"
          value={geos}
          onChange={(e) => setGeos(e.target.value)}
        />
      </div>

      <div className="md:col-span-4 flex justify-end">
        <button
          onClick={apply}
          disabled={saving}
          className={`rounded-xl border px-4 py-2 shadow-sm transition-all
            ${
              saving
                ? "bg-gray-200 text-gray-500 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700 active:scale-95"
            }`}
        >
          {saving ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
              Applying…
            </span>
          ) : (
            "Apply Preferences"
          )}
        </button>
      </div>
    </div>
  );
}