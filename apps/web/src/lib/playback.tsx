"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { API_BASE } from "@/lib/api";
import type { PlaybackState, Track } from "@/lib/types";

type PlaybackContextValue = PlaybackState & {
  playTrack: (track: Track, queue?: Track[]) => void;
  togglePlay: () => void;
  next: () => void;
  previous: () => void;
  setVolume: (v: number) => void;
  seek: (ms: number) => void;
  toggleShuffle: () => void;
  cycleRepeat: () => void;
};

const PlaybackContext = createContext<PlaybackContextValue | null>(null);

async function resolveStreamUrl(trackId: string): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/api/tracks/${trackId}/stream`);
    if (!res.ok) return null;
    const data = (await res.json()) as { url?: string };
    return data.url ?? null;
  } catch {
    return null;
  }
}

export function PlaybackProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [state, setState] = useState<PlaybackState>({
    track: null,
    queue: [],
    isPlaying: false,
    positionMs: 0,
    shuffle: false,
    repeat: "off",
    volume: 0.8,
  });

  useEffect(() => {
    const audio = new Audio();
    audio.preload = "metadata";
    audioRef.current = audio;

    const onTime = () =>
      setState((s) => ({ ...s, positionMs: Math.floor(audio.currentTime * 1000) }));
    const onEnded = () => {
      setState((s) => {
        if (s.repeat === "one" && s.track) {
          audio.currentTime = 0;
          void audio.play();
          return { ...s, isPlaying: true, positionMs: 0 };
        }
        // advance queue
        if (!s.track || s.queue.length === 0) {
          return { ...s, isPlaying: false };
        }
        const idx = s.queue.findIndex((t) => t.id === s.track!.id);
        const nextIdx = idx < 0 ? 0 : (idx + 1) % s.queue.length;
        if (s.repeat === "off" && nextIdx === 0 && idx === s.queue.length - 1) {
          return { ...s, isPlaying: false, positionMs: 0 };
        }
        const nextTrack = s.queue[nextIdx];
        void (async () => {
          const url = nextTrack.streamUrl ?? (await resolveStreamUrl(nextTrack.id));
          if (!url || !audioRef.current) return;
          audioRef.current.src = url;
          await audioRef.current.play().catch(() => undefined);
          setState((prev) => ({
            ...prev,
            track: { ...nextTrack, streamUrl: url },
            isPlaying: true,
            positionMs: 0,
          }));
        })();
        return { ...s, track: nextTrack, positionMs: 0, isPlaying: true };
      });
    };

    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("ended", onEnded);
    return () => {
      audio.pause();
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("ended", onEnded);
      audioRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = state.volume;
  }, [state.volume]);

  const playTrack = useCallback(async (track: Track, queue?: Track[]) => {
    const audio = audioRef.current;
    if (!audio) return;
    const url = track.streamUrl ?? (await resolveStreamUrl(track.id));
    if (!url) {
      console.error("No stream URL for track", track.id);
      return;
    }
    audio.src = url;
    audio.currentTime = 0;
    try {
      await audio.play();
    } catch (err) {
      console.error("Playback failed", err);
    }
    setState((s) => ({
      ...s,
      track: { ...track, streamUrl: url },
      queue: queue ?? s.queue,
      isPlaying: true,
      positionMs: 0,
    }));
  }, []);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !state.track) return;
    if (audio.paused) {
      void audio.play().then(() => setState((s) => ({ ...s, isPlaying: true })));
    } else {
      audio.pause();
      setState((s) => ({ ...s, isPlaying: false }));
    }
  }, [state.track]);

  const next = useCallback(() => {
    setState((s) => {
      if (!s.track || s.queue.length === 0) return s;
      const idx = s.queue.findIndex((t) => t.id === s.track!.id);
      const nextIdx = idx < 0 ? 0 : (idx + 1) % s.queue.length;
      const nextTrack = s.queue[nextIdx];
      void playTrack(nextTrack, s.queue);
      return s;
    });
  }, [playTrack]);

  const previous = useCallback(() => {
    const audio = audioRef.current;
    setState((s) => {
      if (!s.track || s.queue.length === 0) return s;
      if ((audio?.currentTime ?? 0) > 3) {
        if (audio) audio.currentTime = 0;
        return { ...s, positionMs: 0 };
      }
      const idx = s.queue.findIndex((t) => t.id === s.track!.id);
      const prevIdx = idx <= 0 ? s.queue.length - 1 : idx - 1;
      void playTrack(s.queue[prevIdx], s.queue);
      return s;
    });
  }, [playTrack]);

  const setVolume = useCallback((volume: number) => {
    setState((s) => ({ ...s, volume: Math.min(1, Math.max(0, volume)) }));
  }, []);

  const seek = useCallback((positionMs: number) => {
    const audio = audioRef.current;
    if (audio) audio.currentTime = positionMs / 1000;
    setState((s) => ({ ...s, positionMs: Math.max(0, positionMs) }));
  }, []);

  const toggleShuffle = useCallback(() => {
    setState((s) => ({ ...s, shuffle: !s.shuffle }));
  }, []);

  const cycleRepeat = useCallback(() => {
    setState((s) => ({
      ...s,
      repeat: s.repeat === "off" ? "all" : s.repeat === "all" ? "one" : "off",
    }));
  }, []);

  const value = useMemo(
    () => ({
      ...state,
      playTrack,
      togglePlay,
      next,
      previous,
      setVolume,
      seek,
      toggleShuffle,
      cycleRepeat,
    }),
    [
      state,
      playTrack,
      togglePlay,
      next,
      previous,
      setVolume,
      seek,
      toggleShuffle,
      cycleRepeat,
    ],
  );

  return (
    <PlaybackContext.Provider value={value}>{children}</PlaybackContext.Provider>
  );
}

export function usePlayback() {
  const ctx = useContext(PlaybackContext);
  if (!ctx) throw new Error("usePlayback must be used within PlaybackProvider");
  return ctx;
}
