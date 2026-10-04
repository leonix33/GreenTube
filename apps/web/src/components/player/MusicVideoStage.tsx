"use client";

import { useEffect, useRef } from "react";
import { API_BASE } from "@/lib/api";
import { usePlayback } from "@/lib/playback";
import { formatTime } from "@/lib/types";

export function MusicVideoStage() {
  const {
    track,
    musicVideoOpen,
    closeMusicVideo,
    isPlaying,
    positionMs,
    playbackSource,
    registerVideoElement,
  } = usePlayback();

  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !musicVideoOpen || playbackSource !== "video-stream") {
      registerVideoElement(null);
      return;
    }
    registerVideoElement(el);
    const t = window.setTimeout(() => {
      void el.play().catch(() => {});
    }, 200);
    return () => {
      window.clearTimeout(t);
      registerVideoElement(null);
    };
  }, [musicVideoOpen, playbackSource, registerVideoElement, track?.id]);

  if (!musicVideoOpen || !track?.musicVideo) return null;

  const mv = track.musicVideo;
  const title = `${track.title} — ${track.artist}`;

  return (
    <div className="fixed inset-x-0 bottom-[72px] top-16 z-30 flex flex-col bg-black/95 backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-gt-border px-4 py-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-white">{track.title}</p>
          <p className="truncate text-xs text-gt-muted">
            Music video · {track.artist}
            {playbackSource === "youtube" ? " · YouTube" : null}
          </p>
        </div>
        <button
          type="button"
          onClick={closeMusicVideo}
          className="rounded-full border border-white/20 px-3 py-1 text-xs text-white hover:bg-white/10"
        >
          Close
        </button>
      </div>

      <div className="flex min-h-0 flex-1 items-center justify-center p-4">
        {mv.kind === "youtube" ? (
          <iframe
            title={title}
            className="aspect-video w-full max-w-4xl rounded-lg bg-black shadow-2xl ring-1 ring-white/10"
            src={`https://www.youtube.com/embed/${mv.youtubeVideoId}?autoplay=1&rel=0&modestbranding=1`}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <video
            ref={videoRef}
            className="max-h-full w-full max-w-4xl rounded-lg bg-black object-contain shadow-2xl ring-1 ring-white/10"
            src={mv.proxyUrl ?? `${API_BASE}/api/tracks/${track.id}/video`}
            playsInline
            controls={false}
          />
        )}
      </div>

      {playbackSource === "video-stream" ? (
        <div className="border-t border-gt-border px-4 py-2 text-center text-xs text-gt-muted">
          {isPlaying ? "Playing" : "Paused"} · {formatTime(positionMs)}
          {track.durationMs ? ` / ${formatTime(track.durationMs)}` : null}
        </div>
      ) : (
        <p className="border-t border-gt-border px-4 py-2 text-center text-xs text-gt-muted">
          Use YouTube controls for playback
        </p>
      )}
    </div>
  );
}
