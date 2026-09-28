import { CuratedPlaylist } from "@/components/catalog/CuratedPlaylist";

export default function LikedMusicPage() {
  return (
    <CuratedPlaylist
      apiPath="/api/playlists/liked-music"
      gradient="from-rose-600/40 via-purple-950/60 to-gt-charcoal"
    />
  );
}
