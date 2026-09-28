"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { genreGradient, type Genre } from "@/lib/genres";

type GenreListResponse = { genres: Genre[]; source?: string };

export function GenreGrid() {
  const [genres, setGenres] = useState<Genre[]>([]);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet<GenreListResponse>("/api/genres")
      .then((data) => {
        if (cancelled) return;
        setGenres(data.genres);
        setSource(data.source || "");
        setError(null);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-gt-muted">Loading genres…</p>;
  }

  if (error) {
    return (
      <p className="text-sm text-red-400">
        Unable to load catalog ({error}). Start the API on :8000 or check MongoDB connectivity.
      </p>
    );
  }

  return (
    <>
      {source ? (
        <p className="text-xs text-gt-muted">
          Catalog source: {source === "mongodb" ? "database" : "offline demo"}
        </p>
      ) : null}
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {genres.map((genre) => (
        <Link
          key={genre.slug}
          href={`/explore/${encodeURIComponent(genre.slug)}`}
          className={`group relative overflow-hidden rounded-md bg-gradient-to-br px-4 py-8 ring-1 ring-white/5 transition hover:-translate-y-0.5 hover:ring-gt-green/40 ${genreGradient(genre.slug)}`}
        >
          <p className="font-display text-xl text-white">{genre.name}</p>
          <p className="mt-2 text-xs text-white/70">
            {genre.track_count > 0
              ? `${genre.track_count} track${genre.track_count === 1 ? "" : "s"} in demo catalog`
              : "Coming soon — browse & save"}
          </p>
          <span className="absolute bottom-3 right-3 rounded-full bg-black/30 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white/80 opacity-0 transition group-hover:opacity-100">
            Open
          </span>
        </Link>
      ))}
    </div>
    </>
  );
}
