"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { usePlayback } from "@/lib/playback";
import { formatTime } from "@/lib/types";
import { apiTrackToTrack, type ApiTrack } from "@/lib/trackMapper";
import type { Track } from "@/lib/types";

type MusicVideosResponse = {
  tracks: ApiTrack[];
  source: string;
};

export default function VideosPage() {
  const { playTrack, openMusicVideo } = usePlayback();
  const [tracks, setTracks] = useState<Track[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiGet<MusicVideosResponse>("/api/music-videos")
      .then((data) => {
        if (!cancelled) setTracks(data.tracks.map(apiTrackToTrack));
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const watch = (track: Track, queue: Track[]) => {
    playTrack(track, queue);
    window.setTimeout(() => openMusicVideo(), 300);
  };

  return (
    <div className="space-y-6 pb-24">
      <div>
        <h1 className="font-display text-3xl text-white">Music videos</h1>
        <p className="mt-2 max-w-xl text-sm text-gt-muted">
          Official YouTube embeds and hosted video streams linked to your catalog. Attach videos with{" "}
          <code className="text-gt-green">YOUTUBE_API_KEY</code> + admin match, or{" "}
          <code className="text-gt-green">PUT /api/admin/catalog/tracks/&#123;id&#125;/music-video</code>.
        </p>
      </div>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {tracks.length === 0 && !error ? (
        <p className="rounded-md border border-gt-border bg-black/20 px-4 py-8 text-sm text-gt-muted">
          No music videos in the catalog yet. Run admin{" "}
          <code className="text-gt-green">POST /api/admin/catalog/music-videos/match-youtube</code> after
          setting <code className="text-gt-green">YOUTUBE_API_KEY</code>.
        </p>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tracks.map((t) => (
            <li key={t.id}>
              <button
                type="button"
                onClick={() => watch(t, tracks)}
                className="group flex w-full flex-col overflow-hidden rounded-lg border border-gt-border bg-gt-elevated/40 text-left transition hover:border-gt-green/40"
              >
                <div className="relative aspect-video bg-gradient-to-br from-violet-900/60 to-gt-charcoal">
                  {t.musicVideo?.kind === "youtube" ? (
                    <img
                      src={`https://img.youtube.com/vi/${t.musicVideo.youtubeVideoId}/hqdefault.jpg`}
                      alt=""
                      className="h-full w-full object-cover opacity-90"
                    />
                  ) : null}
                  <span className="absolute inset-0 flex items-center justify-center bg-black/30 text-3xl opacity-0 transition group-hover:opacity-100">
                    ▶
                  </span>
                </div>
                <div className="px-3 py-3">
                  <p className="truncate text-sm font-medium text-white">{t.title}</p>
                  <p className="truncate text-xs text-gt-muted">
                    {t.artist} · {formatTime(t.durationMs)}
                  </p>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
