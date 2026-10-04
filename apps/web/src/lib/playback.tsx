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
import {
  pauseSpotify,
  playSpotifyUri,
  pollSpotifyPlayback,
  resolveSpotifyUri,
  resumeSpotify,
  seekSpotify,
  spotifyStatus,
} from "@/lib/spotifyPlayback";

type PlaybackContextValue = PlaybackState & {
  playTrack: (track: Track, queue?: Track[]) => void;
  togglePlay: () => void;
  next: () => void;
  previous: () => void;
  setVolume: (v: number) => void;
  seek: (ms: number) => void;
  toggleShuffle: () => void;
  cycleRepeat: () => void;
  openMusicVideo: () => void;
  closeMusicVideo: () => void;
  registerVideoElement: (el: HTMLVideoElement | null) => void;
  playbackError: string | null;
};

const PlaybackContext = createContext<PlaybackContextValue | null>(null);

function resolveStreamUrl(trackId: string): string {
  return `${API_BASE}/api/tracks/${trackId}/audio`;
}

function loadAndPlay(audio: HTMLAudioElement, url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      audio.removeEventListener("canplay", onReady);
      audio.removeEventListener("error", onError);
    };
    const onReady = () => {
      cleanup();
      void audio.play().then(resolve).catch(reject);
    };
    const onError = () => {
      cleanup();
      reject(new Error("Could not load audio stream"));
    };
    audio.addEventListener("canplay", onReady, { once: true });
    audio.addEventListener("error", onError, { once: true });
    audio.src = url;
    audio.load();
  });
}

export function PlaybackProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const videoListenersCleanupRef = useRef<(() => void) | null>(null);
  const spotifyPollStopRef = useRef<(() => void) | null>(null);
  const spotifyConnectedRef = useRef(false);
  const queueRef = useRef<Track[]>([]);
  const playTrackRef = useRef<(track: Track, queue?: Track[]) => void>(() => {});

  const [playbackError, setPlaybackError] = useState<string | null>(null);
  const [state, setState] = useState<PlaybackState>({
    track: null,
    queue: [],
    isPlaying: false,
    positionMs: 0,
    shuffle: false,
    repeat: "off",
    volume: 0.8,
    playbackSource: "stream",
    musicVideoOpen: false,
  });

  const stopSpotifyPoll = useCallback(() => {
    spotifyPollStopRef.current?.();
    spotifyPollStopRef.current = null;
  }, []);

  const startSpotifyPoll = useCallback(() => {
    stopSpotifyPoll();
    spotifyPollStopRef.current = pollSpotifyPlayback(
      ({ positionMs, durationMs, playing }) => {
        setState((s) => {
          if (s.playbackSource !== "spotify" || !s.track) return s;
          const nextTrack =
            durationMs > 0 && (!s.track.durationMs || s.track.durationMs < durationMs - 500)
              ? { ...s.track, durationMs, previewOnly: false }
              : s.track;
          return {
            ...s,
            track: nextTrack,
            positionMs,
            isPlaying: playing,
          };
        });
      },
      () => {
        setState((s) => {
          if (s.repeat === "one" && s.track?.spotifyUri) {
            void playSpotifyUri(s.track.spotifyUri).catch(() => {});
            return { ...s, isPlaying: true, positionMs: 0 };
          }
          if (!s.track || s.queue.length === 0) {
            return { ...s, isPlaying: false };
          }
          const idx = s.queue.findIndex((t) => t.id === s.track!.id);
          const nextIdx = idx < 0 ? 0 : (idx + 1) % s.queue.length;
          if (s.repeat === "off" && nextIdx === 0 && idx === s.queue.length - 1) {
            return { ...s, isPlaying: false, positionMs: 0 };
          }
          playTrackRef.current(s.queue[nextIdx], s.queue);
          return s;
        });
      },
    );
  }, [stopSpotifyPoll]);

  useEffect(() => {
    const refreshSpotify = () => {
      void spotifyStatus()
        .then((s) => {
          spotifyConnectedRef.current = s.connected;
        })
        .catch(() => {
          spotifyConnectedRef.current = false;
        });
    };
    refreshSpotify();
    window.addEventListener("focus", refreshSpotify);
    window.addEventListener("greentube-spotify-status", refreshSpotify);
    return () => {
      window.removeEventListener("focus", refreshSpotify);
      window.removeEventListener("greentube-spotify-status", refreshSpotify);
    };
  }, []);

  useEffect(() => {
    queueRef.current = state.queue;
  }, [state.queue]);

  useEffect(() => {
    const audio = new Audio();
    audio.preload = "auto";
    audioRef.current = audio;

    const onMeta = () => {
      const durMs = Number.isFinite(audio.duration)
        ? Math.floor(audio.duration * 1000)
        : 0;
      if (durMs <= 0) return;
      setState((s) => {
        if (!s.track || s.playbackSource !== "stream") return s;
        if (s.track.previewOnly || durMs < (s.track.durationMs || Infinity)) {
          return { ...s, track: { ...s.track, durationMs: durMs } };
        }
        if (s.track.durationMs && s.track.durationMs > 0) return s;
        return { ...s, track: { ...s.track, durationMs: durMs } };
      });
    };

    const onTime = () =>
      setState((s) =>
        s.playbackSource === "stream"
          ? { ...s, positionMs: Math.floor(audio.currentTime * 1000) }
          : s,
      );
    const onEnded = () => {
      setState((s) => {
        if (s.playbackSource !== "stream") return s;
        if (s.repeat === "one" && s.track) {
          audio.currentTime = 0;
          void audio.play();
          return { ...s, isPlaying: true, positionMs: 0 };
        }
        if (s.track?.previewOnly) {
          setPlaybackError("30-second preview ended — connect Spotify for full tracks.");
          return { ...s, isPlaying: false };
        }
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
          playTrackRef.current(nextTrack, s.queue);
        })();
        return { ...s, track: nextTrack, positionMs: 0, isPlaying: true };
      });
    };

    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("loadedmetadata", onMeta);
    audio.addEventListener("durationchange", onMeta);
    return () => {
      audio.pause();
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("loadedmetadata", onMeta);
      audio.removeEventListener("durationchange", onMeta);
      audioRef.current = null;
      stopSpotifyPoll();
    };
  }, [stopSpotifyPoll]);

  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = state.volume;
    if (videoRef.current) videoRef.current.volume = state.volume;
  }, [state.volume]);

  const playStream = useCallback(
    async (audio: HTMLAudioElement, track: Track, queue: Track[]) => {
      stopSpotifyPoll();
      void pauseSpotify().catch(() => {});
      const url = track.streamUrl ?? resolveStreamUrl(track.id);
      setState((s) => ({
        ...s,
        track: { ...track, streamUrl: url },
        queue,
        isPlaying: false,
        positionMs: 0,
        playbackSource: "stream",
      }));
      await loadAndPlay(audio, url);
      setState((s) => ({ ...s, isPlaying: true }));
    },
    [stopSpotifyPoll],
  );

  const registerVideoElement = useCallback((el: HTMLVideoElement | null) => {
    videoListenersCleanupRef.current?.();
    videoListenersCleanupRef.current = null;
    videoRef.current = el;
    if (!el) return;
    const onTime = () => {
      setState((s) =>
        s.playbackSource === "video-stream"
          ? { ...s, positionMs: Math.floor(el.currentTime * 1000) }
          : s,
      );
    };
    const onMeta = () => {
      const durMs = Number.isFinite(el.duration) ? Math.floor(el.duration * 1000) : 0;
      if (durMs <= 0) return;
      setState((s) => {
        if (!s.track || s.playbackSource !== "video-stream") return s;
        return { ...s, track: { ...s.track, durationMs: durMs } };
      });
    };
    const onEnded = () => {
      setState((s) => {
        if (s.playbackSource !== "video-stream") return s;
        return { ...s, isPlaying: false, musicVideoOpen: false, playbackSource: "stream" };
      });
    };
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("ended", onEnded);
    videoListenersCleanupRef.current = () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("ended", onEnded);
    };
  }, []);

  const closeMusicVideo = useCallback(() => {
    videoRef.current?.pause();
    setState((s) => ({
      ...s,
      musicVideoOpen: false,
      playbackSource: s.playbackSource === "youtube" || s.playbackSource === "video-stream" ? "stream" : s.playbackSource,
      isPlaying: false,
    }));
  }, []);

  const openMusicVideo = useCallback(() => {
    const audio = audioRef.current;
    if (audio) audio.pause();
    stopSpotifyPoll();
    void pauseSpotify().catch(() => {});
    setState((s) => {
      if (!s.track?.musicVideo) return s;
      const kind = s.track.musicVideo.kind;
      if (kind === "youtube") {
        return {
          ...s,
          musicVideoOpen: true,
          playbackSource: "youtube",
          isPlaying: true,
        };
      }
      return {
        ...s,
        musicVideoOpen: true,
        playbackSource: "video-stream",
        isPlaying: false,
        positionMs: 0,
      };
    });
  }, [stopSpotifyPoll]);

  const playTrack = useCallback(
    async (track: Track, queue?: Track[]) => {
      const audio = audioRef.current;
      if (!audio) return;
      const q = queue ?? queueRef.current;
      setPlaybackError(null);
      closeMusicVideo();

      let spotify = { configured: false, connected: false };
      try {
        spotify = await spotifyStatus();
      } catch {
        /* API unreachable — audio-only playback */
      }
      spotifyConnectedRef.current = spotify.connected;

      if (spotify.connected) {
        let uri = track.spotifyUri;
        if (!uri) {
          uri = (await resolveSpotifyUri(track.title, track.artist)) ?? undefined;
        }
        if (uri) {
          try {
            audio.pause();
            audio.removeAttribute("src");
            audio.load();
            stopSpotifyPoll();
            await playSpotifyUri(uri);
            const enriched: Track = {
              ...track,
              spotifyUri: uri,
              previewOnly: false,
            };
            setState((s) => ({
              ...s,
              track: enriched,
              queue: q,
              isPlaying: true,
              positionMs: 0,
              playbackSource: "spotify",
            }));
            startSpotifyPoll();
            return;
          } catch (err) {
            console.warn("Spotify playback failed, falling back to stream", err);
            if (err instanceof Error) {
              setPlaybackError(err.message);
            }
          }
        }
      }

      if (track.previewOnly) {
        setPlaybackError(
          "No full stream for this track. Open Liked → Connect Spotify (Premium) for full songs.",
        );
        setState((s) => ({ ...s, isPlaying: false }));
        return;
      }

      try {
        await playStream(audio, track, q);
      } catch (err) {
        console.error("Playback failed", err);
        setPlaybackError(
          "Could not play this track. Connect Spotify on the Liked page for full-length playback.",
        );
        setState((s) => ({ ...s, isPlaying: false, playbackSource: "stream" }));
      }
    },
    [playStream, startSpotifyPoll, stopSpotifyPoll, closeMusicVideo],
  );

  useEffect(() => {
    playTrackRef.current = (track, queue) => {
      void playTrack(track, queue);
    };
  }, [playTrack]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!state.track) return;

    if (state.playbackSource === "youtube") return;

    if (state.playbackSource === "video-stream") {
      const video = videoRef.current;
      if (!video) return;
      if (state.isPlaying) {
        video.pause();
        setState((s) => ({ ...s, isPlaying: false }));
      } else {
        void video
          .play()
          .then(() => {
            setPlaybackError(null);
            setState((s) => ({ ...s, isPlaying: true }));
          })
          .catch(() => setPlaybackError("Could not play video."));
      }
      return;
    }

    if (state.playbackSource === "spotify") {
      if (state.isPlaying) {
        void pauseSpotify()
          .then(() => setState((s) => ({ ...s, isPlaying: false })))
          .catch(() => setPlaybackError("Could not pause Spotify."));
      } else {
        void resumeSpotify()
          .then(() => {
            setPlaybackError(null);
            setState((s) => ({ ...s, isPlaying: true }));
          })
          .catch((e: Error) => setPlaybackError(e.message));
      }
      return;
    }

    if (!audio) return;
    if (audio.paused) {
      void audio
        .play()
        .then(() => {
          setPlaybackError(null);
          setState((s) => ({ ...s, isPlaying: true }));
        })
        .catch(() => {
          setPlaybackError("Tap play again or choose another track.");
        });
    } else {
      audio.pause();
      setState((s) => ({ ...s, isPlaying: false }));
    }
  }, [state.track, state.isPlaying, state.playbackSource]);

  const next = useCallback(() => {
    setState((s) => {
      if (!s.track || s.queue.length === 0) return s;
      const idx = s.queue.findIndex((t) => t.id === s.track!.id);
      const nextIdx = idx < 0 ? 0 : (idx + 1) % s.queue.length;
      void playTrack(s.queue[nextIdx], s.queue);
      return s;
    });
  }, [playTrack]);

  const previous = useCallback(() => {
    const audio = audioRef.current;
    setState((s) => {
      if (!s.track || s.queue.length === 0) return s;
      if (s.playbackSource === "stream" && (audio?.currentTime ?? 0) > 3) {
        if (audio) audio.currentTime = 0;
        return { ...s, positionMs: 0 };
      }
      if (s.playbackSource === "spotify" && s.positionMs > 3000) {
        void seekSpotify(0);
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

  const seek = useCallback(
    (positionMs: number) => {
      const ms = Math.max(0, positionMs);
      if (state.playbackSource === "spotify") {
        void seekSpotify(ms);
        setState((s) => ({ ...s, positionMs: ms }));
        return;
      }
      if (state.playbackSource === "video-stream") {
        const video = videoRef.current;
        if (video) video.currentTime = ms / 1000;
        setState((s) => ({ ...s, positionMs: ms }));
        return;
      }
      const audio = audioRef.current;
      if (audio) audio.currentTime = ms / 1000;
      setState((s) => ({ ...s, positionMs: ms }));
    },
    [state.playbackSource],
  );

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
      playbackError,
      playTrack,
      togglePlay,
      next,
      previous,
      setVolume,
      seek,
      toggleShuffle,
      cycleRepeat,
      openMusicVideo,
      closeMusicVideo,
      registerVideoElement,
    }),
    [
      state,
      playbackError,
      playTrack,
      togglePlay,
      next,
      previous,
      setVolume,
      seek,
      toggleShuffle,
      cycleRepeat,
      openMusicVideo,
      closeMusicVideo,
      registerVideoElement,
    ],
  );

  return (
    <PlaybackContext.Provider value={value}>
      {children}
      {playbackError ? (
        <div
          className="fixed bottom-20 left-1/2 z-50 max-w-md -translate-x-1/2 rounded-md border border-red-500/40 bg-black/90 px-4 py-2 text-center text-sm text-red-300"
          role="status"
        >
          {playbackError}
        </div>
      ) : null}
    </PlaybackContext.Provider>
  );
}

export function usePlayback() {
  const ctx = useContext(PlaybackContext);
  if (!ctx) throw new Error("usePlayback must be used within PlaybackProvider");
  return ctx;
}
