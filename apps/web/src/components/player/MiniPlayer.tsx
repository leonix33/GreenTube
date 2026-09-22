"use client";

import { formatTime } from "@/lib/types";
import { usePlayback } from "@/lib/playback";

export function MiniPlayer() {
  const {
    track,
    isPlaying,
    positionMs,
    volume,
    togglePlay,
    next,
    previous,
    setVolume,
    seek,
    shuffle,
    repeat,
    toggleShuffle,
    cycleRepeat,
  } = usePlayback();

  if (!track) return null;

  const progress = track.durationMs
    ? Math.min(100, (positionMs / track.durationMs) * 100)
    : 0;

  return (
    <footer className="shadow-player z-20 flex h-[72px] shrink-0 items-center gap-4 border-t border-gt-border bg-gt-panel/95 px-4 backdrop-blur-xl">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded bg-gradient-to-br from-gt-green/80 to-emerald-900 text-xs font-bold text-black">
          {track.title.slice(0, 2).toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-white">{track.title}</p>
          <p className="truncate text-xs text-gt-muted">{track.artist}</p>
        </div>
      </div>

      <div className="flex w-[420px] max-w-[45%] flex-col items-center gap-1">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggleShuffle}
            className={`text-xs ${shuffle ? "text-gt-green" : "text-gt-muted"} hover:text-white`}
            aria-label="Shuffle"
          >
            ⇄
          </button>
          <button
            type="button"
            onClick={previous}
            className="text-gt-muted hover:text-white"
            aria-label="Previous"
          >
            ◀︎
          </button>
          <button
            type="button"
            onClick={togglePlay}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-black transition hover:scale-105"
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? "❚❚" : "▶"}
          </button>
          <button
            type="button"
            onClick={next}
            className="text-gt-muted hover:text-white"
            aria-label="Next"
          >
            ▶︎
          </button>
          <button
            type="button"
            onClick={cycleRepeat}
            className={`text-xs ${repeat !== "off" ? "text-gt-green" : "text-gt-muted"} hover:text-white`}
            aria-label="Repeat"
          >
            {repeat === "one" ? "1" : "↻"}
          </button>
        </div>
        <div className="flex w-full items-center gap-2 text-[10px] text-gt-muted">
          <span>{formatTime(positionMs)}</span>
          <input
            type="range"
            min={0}
            max={track.durationMs}
            value={positionMs}
            onChange={(e) => seek(Number(e.target.value))}
            className="h-1 flex-1 cursor-pointer accent-gt-green"
            aria-label="Seek"
            style={{ backgroundSize: `${progress}% 100%` }}
          />
          <span>{formatTime(track.durationMs)}</span>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-end gap-2">
        <span className="text-xs text-gt-muted">Vol</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={volume}
          onChange={(e) => setVolume(Number(e.target.value))}
          className="w-24 accent-gt-green"
          aria-label="Volume"
        />
      </div>
    </footer>
  );
}
