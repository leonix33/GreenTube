import type { MusicVideo, Track } from "@/lib/types";

export type ApiTrack = {
  id: string;
  title: string;
  artist: string;
  album?: string | null;
  duration_ms: number;
  preview_only?: boolean;
  spotify_uri?: string | null;
  has_music_video?: boolean;
  music_video?: {
    kind: string;
    youtube_video_id?: string | null;
    video_url?: string | null;
    proxy_url?: string | null;
  } | null;
};

export function apiTrackToTrack(t: ApiTrack): Track {
  let musicVideo: MusicVideo | undefined;
  const mv = t.music_video;
  if (mv?.kind === "youtube" && mv.youtube_video_id) {
    musicVideo = { kind: "youtube", youtubeVideoId: mv.youtube_video_id };
  } else if (mv?.kind === "stream") {
    musicVideo = {
      kind: "stream",
      videoUrl: mv.video_url ?? undefined,
      proxyUrl: mv.proxy_url ?? undefined,
    };
  }

  return {
    id: t.id,
    title: t.title,
    artist: t.artist,
    album: t.album ?? undefined,
    durationMs: t.duration_ms,
    previewOnly: t.preview_only,
    spotifyUri: t.spotify_uri ?? undefined,
    hasMusicVideo: Boolean(t.has_music_video || musicVideo),
    musicVideo,
  };
}
