"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { DEMO_TRACKS, type PlaybackState, type Track } from "@/lib/types";

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

export function PlaybackProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PlaybackState>({
    track: DEMO_TRACKS[0],
    queue: DEMO_TRACKS,
    isPlaying: false,
    positionMs: 0,
    shuffle: false,
    repeat: "off",
    volume: 0.8,
  });

  const playTrack = useCallback((track: Track, queue?: Track[]) => {
    setState((s) => ({
      ...s,
      track,
      queue: queue ?? s.queue,
      isPlaying: true,
      positionMs: 0,
    }));
  }, []);

  const togglePlay = useCallback(() => {
    setState((s) => ({ ...s, isPlaying: !s.isPlaying }));
  }, []);

  const next = useCallback(() => {
    setState((s) => {
      if (!s.track || s.queue.length === 0) return s;
      const idx = s.queue.findIndex((t) => t.id === s.track!.id);
      const nextIdx = idx < 0 ? 0 : (idx + 1) % s.queue.length;
      return { ...s, track: s.queue[nextIdx], positionMs: 0, isPlaying: true };
    });
  }, []);

  const previous = useCallback(() => {
    setState((s) => {
      if (!s.track || s.queue.length === 0) return s;
      if (s.positionMs > 3000) return { ...s, positionMs: 0 };
      const idx = s.queue.findIndex((t) => t.id === s.track!.id);
      const prevIdx = idx <= 0 ? s.queue.length - 1 : idx - 1;
      return { ...s, track: s.queue[prevIdx], positionMs: 0, isPlaying: true };
    });
  }, []);

  const setVolume = useCallback((volume: number) => {
    setState((s) => ({ ...s, volume: Math.min(1, Math.max(0, volume)) }));
  }, []);

  const seek = useCallback((positionMs: number) => {
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
