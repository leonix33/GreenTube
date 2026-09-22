export type Track = {
  id: string;
  title: string;
  artist: string;
  album?: string;
  artworkUrl?: string;
  durationMs: number;
};

export type PlaybackState = {
  track: Track | null;
  queue: Track[];
  isPlaying: boolean;
  positionMs: number;
  shuffle: boolean;
  repeat: "off" | "one" | "all";
  volume: number;
};

export const DEMO_TRACKS: Track[] = [
  {
    id: "t1",
    title: "Lagos Nights",
    artist: "Amina Okoye",
    album: "Atlantic Pulse",
    durationMs: 214000,
    artworkUrl: undefined,
  },
  {
    id: "t2",
    title: "Green Room",
    artist: "North Harbor",
    album: "After Hours",
    durationMs: 198000,
  },
  {
    id: "t3",
    title: "Paper Lanterns",
    artist: "Mira Chen",
    album: "Soft Circuits",
    durationMs: 241000,
  },
  {
    id: "t4",
    title: "Dust & Chrome",
    artist: "Kiln",
    album: "Foundry",
    durationMs: 187000,
  },
  {
    id: "t5",
    title: "Sunday Market",
    artist: "Kofi Mensah",
    album: "Open Air",
    durationMs: 226000,
  },
];

export function formatTime(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
