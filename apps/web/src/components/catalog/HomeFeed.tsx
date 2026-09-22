"use client";

import { DEMO_TRACKS, type Track } from "@/lib/types";
import { usePlayback } from "@/lib/playback";

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
          Your mixes, made from listening signals — not a clone of anyone&apos;s catalog.
        </p>
      </div>

      <section>
        <p className="gt-section-label mb-3">Quick picks</p>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {DEMO_TRACKS.map((t) => (
            <AlbumCard
              key={t.id}
              track={t}
              onPlay={() => playTrack(t, DEMO_TRACKS)}
            />
          ))}
        </div>
      </section>

      <section>
        <p className="gt-section-label mb-3">Listen again</p>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {[...DEMO_TRACKS].reverse().map((t) => (
            <AlbumCard
              key={`again-${t.id}`}
              track={t}
              onPlay={() => playTrack(t, DEMO_TRACKS)}
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
