"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import type { Track } from "@/lib/types";
import { usePlayback } from "@/lib/playback";

type HomeItem = {
  id: string;
  title: string;
  artist: string;
  album?: string | null;
  duration_ms: number;
};

type HomeResponse = {
  sections: { id: string; title: string; items: HomeItem[] }[];
  source: string;
};

function toTrack(item: HomeItem): Track {
  return {
    id: item.id,
    title: item.title,
    artist: item.artist,
    album: item.album ?? undefined,
    durationMs: item.duration_ms,
  };
}

function AlbumCard({
  track,
  onPlay,
}: {
  track: Track;
  onPlay: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onPlay}
      className="group w-[148px] shrink-0 text-left transition hover:-translate-y-0.5"
    >
      <div className="mb-3 aspect-square overflow-hidden rounded-md bg-gradient-to-br from-emerald-700/60 via-gt-elevated to-gt-charcoal shadow-lg ring-1 ring-white/5">
        <div className="flex h-full w-full items-end justify-between p-3">
          <span className="text-2xl font-display text-white/90">{track.title[0]}</span>
          <span className="rounded-full bg-gt-green px-2 py-1 text-[10px] font-bold text-black opacity-0 transition group-hover:opacity-100">
            ▶
          </span>
        </div>
      </div>
      <p className="truncate text-sm font-medium text-white">{track.album ?? track.title}</p>
      <p className="truncate text-xs text-gt-muted">{track.artist}</p>
    </button>
  );
}

function MixCard({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="w-[180px] shrink-0 overflow-hidden rounded-md bg-gt-elevated ring-1 ring-white/5">
      <div className="h-28 bg-gradient-to-br from-gt-green/40 via-teal-900/50 to-gt-charcoal p-4">
        <p className="font-display text-lg leading-tight text-white">{title}</p>
      </div>
      <div className="px-3 py-2">
        <p className="text-xs text-gt-muted">{subtitle}</p>
      </div>
    </div>
  );
}

export function HomeFeed() {
  const { playTrack } = usePlayback();
  const [tracks, setTracks] = useState<Track[]>([]);
  const [source, setSource] = useState<string>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiGet<HomeResponse>("/api/home")
      .then((data) => {
        if (cancelled) return;
        const quick =
          data.sections.find((s) => s.id === "quick_picks")?.items ?? [];
        setTracks(quick.map(toTrack));
        setSource(data.source);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="space-y-10 pb-4">
      <div>
        <h1 className="font-display text-3xl tracking-tight text-white md:text-4xl">
          {greeting}
        </h1>
        <p className="mt-1 text-sm text-gt-muted">
          Open/demo catalog via provider adapters
          {source !== "loading" ? ` · ${source}` : ""}.
        </p>
        {error ? (
          <p className="mt-2 text-sm text-red-400">
            API unreachable ({error}). Start the API on :8000.
          </p>
        ) : null}
      </div>

      <section>
        <p className="gt-section-label mb-3">Quick picks</p>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {tracks.map((t) => (
            <AlbumCard
              key={t.id}
              track={t}
              onPlay={() => playTrack(t, tracks)}
            />
          ))}
          {!error && tracks.length === 0 ? (
            <p className="text-sm text-gt-muted">Loading catalog…</p>
          ) : null}
        </div>
      </section>

      <section>
        <p className="gt-section-label mb-3">Listen again</p>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {[...tracks].reverse().map((t) => (
            <AlbumCard
              key={`again-${t.id}`}
              track={t}
              onPlay={() => playTrack(t, tracks)}
            />
          ))}
        </div>
      </section>

      <section>
        <p className="gt-section-label mb-3">Made for you</p>
        <div className="flex gap-4 overflow-x-auto pb-2">
          <MixCard title="My Mix 1" subtitle="Afrobeats · electronic · evening" />
          <MixCard title="My Mix 2" subtitle="Focus · instrumental" />
          <MixCard title="Discover Mix" subtitle="New artists matched to your taste" />
          <MixCard title="New Release Mix" subtitle="Fresh drops in your lanes" />
        </div>
      </section>
    </div>
  );
}
