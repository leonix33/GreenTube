import { CuratedPlaylist } from "@/components/catalog/CuratedPlaylist";

export default function MajorAfrobeatsPlaylistPage() {
  return (
    <CuratedPlaylist
      apiPath="/api/playlists/major-afrobeats"
      gradient="from-amber-500/40 via-orange-900/50 to-gt-charcoal"
    />
  );
}
