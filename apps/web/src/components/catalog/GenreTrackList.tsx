"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import type { Track } from "@/lib/types";
import { usePlayback } from "@/lib/playback";
import { formatTime } from "@/lib/types";

type ApiTrack = {
  id: string;
  title: string;
  artist: string;
  album?: string | null;
  duration_ms: number;
  genres?: string[] | null;
};

type GenreTracksResponse = {
  slug: string;
  name: string;
  tracks: ApiTrack[];
  source?: string;
};

function toTrack(t: ApiTrack): Track {
  return {
    id: t.id,
    title: t.title,
    artist: t.artist,
    album: t.album ?? undefined,
    durationMs: t.duration_ms,
  };
}

export function GenreTrackList({ slug }: { slug: string }) {
  const { playTrack } = usePlayback();
  const [name, setName] = useState(slug);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [raw, setRaw] = useState<ApiTrack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet<GenreTracksResponse>(`/api/genres/${encodeURIComponent(slug)}/tracks`)
      .then((data) => {
        if (cancelled) return;
        setName(data.name);
        setRaw(data.tracks);
        setTracks(data.tracks.map(toTrack));
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
  }, [slug]);

  if (loading) {
    return <p className="text-sm text-gt-muted">Loading tracks…</p>;
  }

  if (error) {
    return (
      <p className="text-sm text-red-400">
        Unable to load catalog ({error}). Provider may be unavailable — try again later.
      </p>
    );
  }

  if (!tracks.length) {
    return (
      <div className="rounded-md border border-dashed border-gt-border bg-gt-elevated/40 px-6 py-10 text-center">
        <p className="font-display text-lg text-white">No tracks available yet</p>
        <p className="mt-2 text-sm text-gt-muted">
          {name} is ready in browse — import or seed the catalog to fill this genre.
        </p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-gt-border overflow-hidden rounded-md ring-1 ring-white/5">
      {raw.map((row, index) => {
        const track = tracks[index];
        return (
          <li key={row.id}>
            <button
              type="button"
              onClick={() => playTrack(track, tracks)}
              className="flex w-full items-center gap-4 bg-gt-elevated/40 px-4 py-3 text-left transition hover:bg-white/5"
            >
              <span className="w-6 text-center text-xs text-gt-muted">{index + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-white">{row.title}</p>
                <p className="truncate text-xs text-gt-muted">
                  {row.artist}
                  {row.album ? ` · ${row.album}` : ""}
                </p>
              </div>
              <span className="text-xs tabular-nums text-gt-muted">
                {formatTime(row.duration_ms)}
              </span>
              <span className="rounded-full bg-gt-green px-2 py-1 text-[10px] font-bold text-black">
                ▶
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
