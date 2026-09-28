"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";

type ImportResult = {
  provider: string;
  requested: number;
  imported: number;
  updated: number;
  duplicates: number;
  failed: number;
};

type Stats = {
  total_tracks: number;
  playable_tracks: number;
  metadata_only_tracks: number;
  artists: number;
  albums: number;
  genres: number;
  tracks_by_provider: Record<string, number>;
  mongodb_connected?: boolean;
  providers?: Record<string, boolean>;
  source?: string;
};

export default function CatalogAdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [provider, setProvider] = useState("local");
  const [query, setQuery] = useState("");
  const [genre, setGenre] = useState("");
  const [limit, setLimit] = useState(50);
  const [stats, setStats] = useState<Stats | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadStats() {
    setError(null);
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/catalog/stats`, {
        headers: { "X-Admin-Key": adminKey },
      });
      if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
      setStats((await res.json()) as Stats);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load catalog stats");
    } finally {
      setBusy(false);
    }
  }

  async function runImport() {
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      const params = new URLSearchParams({ limit: String(limit) });
      if (query.trim()) params.set("query", query.trim());
      if (genre.trim()) params.set("genre", genre.trim());
      const res = await fetch(
        `${API_BASE}/api/admin/catalog/import/${provider}?${params.toString()}`,
        { method: "POST", headers: { "X-Admin-Key": adminKey } },
      );
      if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
      setResult((await res.json()) as ImportResult);
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 pb-10">
      <div>
        <h1 className="font-display text-3xl text-white">GreenTube Catalog</h1>
        <p className="mt-2 text-sm text-gt-muted">
          Development catalog controls. Provider API keys stay on the server — enter your admin
          key only (not Jamendo credentials).
        </p>
      </div>

      <section className="space-y-3 rounded-md bg-gt-elevated p-5 ring-1 ring-white/5">
        <label className="block text-sm text-gt-muted">
          Admin key
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            className="mt-1 w-full rounded-md border border-gt-border bg-black/30 px-3 py-2 text-sm text-white"
            placeholder="X-Admin-Key (matches ADMIN_API_KEY on API)"
          />
        </label>
        <button
          type="button"
          disabled={busy || !adminKey}
          onClick={loadStats}
          className="rounded-full bg-gt-green px-4 py-2 text-sm font-semibold text-black disabled:opacity-50"
        >
          Refresh stats
        </button>
      </section>

      {stats ? (
        <section className="grid gap-3 sm:grid-cols-2">
          <Stat label="Total tracks" value={stats.total_tracks} />
          <Stat label="Playable tracks" value={stats.playable_tracks} />
          <Stat label="Artists" value={stats.artists} />
          <Stat label="Albums" value={stats.albums} />
          <Stat label="Genres" value={stats.genres} />
          <Stat label="Metadata-only" value={stats.metadata_only_tracks} />
          <div className="sm:col-span-2 rounded-md bg-black/25 p-4 text-sm text-gt-muted">
            <p className="font-medium text-white">Provider breakdown</p>
            <ul className="mt-2 space-y-1">
              {Object.entries(stats.tracks_by_provider || {}).map(([name, count]) => (
                <li key={name}>
                  {name}: {count}
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}

      <section className="space-y-3 rounded-md bg-gt-elevated p-5 ring-1 ring-white/5">
        <h2 className="font-display text-xl text-white">Import</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm text-gt-muted">
            Provider
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="mt-1 w-full rounded-md border border-gt-border bg-black/30 px-3 py-2 text-sm text-white"
            >
              <option value="local">Local</option>
              <option value="jamendo">Jamendo</option>
              <option value="audius">Audius</option>
              <option value="musicbrainz">MusicBrainz (metadata)</option>
            </select>
          </label>
          <label className="text-sm text-gt-muted">
            Limit
            <input
              type="number"
              min={1}
              max={200}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-gt-border bg-black/30 px-3 py-2 text-sm text-white"
            />
          </label>
          <label className="text-sm text-gt-muted sm:col-span-2">
            Search query
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="mt-1 w-full rounded-md border border-gt-border bg-black/30 px-3 py-2 text-sm text-white"
              placeholder="Optional provider search"
            />
          </label>
          <label className="text-sm text-gt-muted sm:col-span-2">
            Genre / tags
            <input
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              className="mt-1 w-full rounded-md border border-gt-border bg-black/30 px-3 py-2 text-sm text-white"
              placeholder="e.g. afrobeats"
            />
          </label>
        </div>
        <button
          type="button"
          disabled={busy || !adminKey}
          onClick={runImport}
          className="rounded-full bg-gt-green px-4 py-2 text-sm font-semibold text-black disabled:opacity-50"
        >
          Run import
        </button>
      </section>

      {result ? (
        <pre className="overflow-x-auto rounded-md bg-black/40 p-4 text-xs text-green-100">
          {JSON.stringify(result, null, 2)}
        </pre>
      ) : null}

      {error ? <p className="text-sm text-red-400">{error}</p> : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-black/25 px-4 py-3 ring-1 ring-white/5">
      <p className="text-xs uppercase tracking-wide text-gt-muted">{label}</p>
      <p className="mt-1 font-display text-2xl text-white">{value}</p>
    </div>
  );
}
