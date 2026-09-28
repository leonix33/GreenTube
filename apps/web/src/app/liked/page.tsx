"use client";

import { useState } from "react";
import { CuratedPlaylist } from "@/components/catalog/CuratedPlaylist";
import { SpotifyConnect } from "@/components/integrations/SpotifyConnect";

export default function LikedPage() {
  const [reloadKey, setReloadKey] = useState(0);

  return (
    <div className="space-y-4">
      <SpotifyConnect onLinked={() => setReloadKey((k) => k + 1)} />
      <CuratedPlaylist
        key={reloadKey}
        apiPath="/api/playlists/liked-music"
        backHref="/"
        gradient="from-rose-600/40 via-purple-950/60 to-gt-charcoal"
      />
    </div>
  );
}
