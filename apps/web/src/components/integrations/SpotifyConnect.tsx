"use client";

import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";
import { spotifyStatus } from "@/lib/spotifyPlayback";

export function SpotifyConnect({ onLinked }: { onLinked?: () => void }) {
  const [configured, setConfigured] = useState(false);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const s = await spotifyStatus();
    setConfigured(s.configured);
    setConnected(s.connected);
  }, []);

  useEffect(() => {
    void refresh();
    const params = new URLSearchParams(window.location.search);
    if (params.get("spotify") === "connected") {
      setMessage("Spotify connected — link your Liked songs for full playback.");
      void refresh();
      window.dispatchEvent(new Event("greentube-spotify-status"));
    }
  }, [refresh]);

  const connect = () => {
    window.location.href = `${API_BASE}/api/integrations/spotify/login`;
  };

  const linkLiked = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/integrations/spotify/match-liked`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || res.statusText);
      }
      const data = (await res.json()) as { matched: number; total: number };
      setMessage(`Linked ${data.matched} / ${data.total} Liked tracks on Spotify.`);
      window.dispatchEvent(new Event("greentube-spotify-status"));
      onLinked?.();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Link failed");
    } finally {
      setBusy(false);
    }
  };

  if (!configured) {
    return (
      <p className="rounded-md border border-amber-500/30 bg-amber-950/30 px-3 py-2 text-sm text-amber-100/90">
        Add <code className="text-gt-green">SPOTIFY_CLIENT_ID</code> and{" "}
        <code className="text-gt-green">SPOTIFY_CLIENT_SECRET</code> to{" "}
        <code className="text-gt-green">services/api/.env</code>, then restart the API.
      </p>
    );
  }

  return (
    <div className="space-y-2 rounded-md border border-gt-border bg-gt-elevated/40 px-4 py-3">
      <p className="text-sm font-medium text-white">Full songs via Spotify</p>
      <p className="text-xs text-gt-muted">
        Requires a Spotify Premium account. GreenTube plays through Spotify&apos;s official player
        (no ripping).
      </p>
      <div className="flex flex-wrap gap-2 pt-1">
        {!connected ? (
          <button
            type="button"
            onClick={connect}
            className="rounded-full bg-[#1DB954] px-4 py-2 text-sm font-bold text-black hover:brightness-110"
          >
            Connect Spotify
          </button>
        ) : (
          <>
            <span className="self-center text-xs text-gt-green">Connected</span>
            <button
              type="button"
              disabled={busy}
              onClick={() => void linkLiked()}
              className="rounded-full border border-white/20 px-4 py-2 text-sm text-white hover:bg-white/10 disabled:opacity-50"
            >
              {busy ? "Linking…" : "Link Liked to Spotify"}
            </button>
          </>
        )}
      </div>
      {message ? <p className="text-xs text-gt-muted">{message}</p> : null}
    </div>
  );
}
