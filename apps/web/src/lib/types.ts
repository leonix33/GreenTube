export type MusicVideo =
  | { kind: "youtube"; youtubeVideoId: string }
  | { kind: "stream"; videoUrl?: string; proxyUrl?: string };

export type Track = {
  id: string;
  title: string;
  artist: string;
  album?: string;
  artworkUrl?: string;
  durationMs: number;
  streamUrl?: string;
  previewOnly?: boolean;
  spotifyUri?: string;
  hasMusicVideo?: boolean;
  musicVideo?: MusicVideo;
};

export type PlaybackSource = "stream" | "spotify" | "video-stream" | "youtube";

export type PlaybackState = {
  track: Track | null;
  queue: Track[];
  isPlaying: boolean;
  positionMs: number;
  shuffle: boolean;
  repeat: "off" | "one" | "all";
  volume: number;
  playbackSource: PlaybackSource;
  musicVideoOpen: boolean;
};

export function formatTime(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
