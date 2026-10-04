"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { usePlayback } from "@/lib/playback";
import { formatTime } from "@/lib/types";
import { apiTrackToTrack, type ApiTrack } from "@/lib/trackMapper";
import type { Track } from "@/lib/types";

type PlaylistResponse = {
  id: string;
  title: string;
  description: string;
  track_count: number;
  tracks: ApiTrack[];
};

export function CuratedPlaylist({
  apiPath,
  backHref = "/playlists",
  gradient = "from-violet-600/50 via-gt-charcoal to-gt-charcoal",
}: {
  apiPath: string;
  backHref?: string;
  gradient?: string;
}) {
  const { playTrack } = usePlayback();
  const [playlist, setPlaylist] = useState<PlaylistResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tracks, setTracks] = useState<Track[]>([]);

  useEffect(() => {
    let cancelled = false;
    apiGet<PlaylistResponse>(apiPath)
      .then((data) => {
        if (cancelled) return;
        setPlaylist(data);
        setTracks(data.tracks.map(apiTrackToTrack));
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [apiPath]);

  return (
    <div className="space-y-6 pb-24">
      <Link href={backHref} className="text-xs text-gt-muted hover:text-white">
        ← Playlists
      </Link>
      <div
        className={`rounded-lg bg-gradient-to-br px-6 py-8 ring-1 ring-white/5 ${gradient}`}
      >
        <p className="text-xs font-medium uppercase tracking-wide text-white/70">Playlist</p>
        <h1 className="font-display text-3xl text-white md:text-4xl">
          {playlist?.title ?? "Loading…"}
        </h1>
        <p className="mt-2 max-w-xl text-sm text-white/80">
          {playlist?.description ?? "Curated from your GreenTube catalog."}
        </p>
        {tracks.length > 0 ? (
          <button
            type="button"
            onClick={() => playTrack(tracks[0], tracks)}
            className="mt-5 rounded-full bg-gt-green px-6 py-2.5 text-sm font-bold text-black hover:brightness-110"
          >
            Play all · {tracks.length} tracks
          </button>
        ) : null}
      </div>

      {error ? (
        <p className="text-sm text-red-400">
          Could not load playlist ({error}). If this is Liked Music, run{" "}
          <code className="text-gt-green">import_liked_music.py</code> on the API.
        </p>
      ) : null}

      <ol className="divide-y divide-gt-border rounded-md border border-gt-border bg-black/20">
        {!error && tracks.length === 0 ? (
          <li className="px-4 py-6 text-sm text-gt-muted">Loading…</li>
        ) : null}
        {tracks.map((t, i) => (
          <li key={t.id}>
            <button
              type="button"
              onClick={() => playTrack(t, tracks)}
              className="flex w-full items-center gap-4 px-4 py-3 text-left hover:bg-white/5"
            >
              <span className="w-6 text-sm text-gt-muted">{i + 1}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-white">{t.title}</span>
                <span className="block truncate text-xs text-gt-muted">
                  {t.artist}
                  {t.previewOnly && !t.spotifyUri ? (
                    <span className="ml-2 text-amber-200/80">· full song needs Spotify</span>
                  ) : t.spotifyUri ? (
                    <span className="ml-2 text-[#1DB954]/90">· Spotify ready</span>
                  ) : null}
                </span>
              </span>
              <span className="text-xs text-gt-muted">{formatTime(t.durationMs)}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
