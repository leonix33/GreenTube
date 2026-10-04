import { API_BASE } from "@/lib/api";

declare global {
  interface Window {
    Spotify?: {
      Player: new (opts: {
        name: string;
        getOAuthToken: (cb: (token: string) => void) => void;
        volume?: number;
      }) => SpotifyPlayer;
    };
    onSpotifyWebPlaybackSDKReady?: () => void;
  }
}

type SpotifyPlayer = {
  connect: () => Promise<boolean>;
  disconnect: () => void;
  addListener: (event: string, cb: (payload: { device_id?: string }) => void) => void;
  removeListener: (event: string) => void;
  activateElement: () => Promise<void>;
};

let scriptPromise: Promise<void> | null = null;
let player: SpotifyPlayer | null = null;
let deviceId: string | null = null;
let readyPromise: Promise<string> | null = null;

function loadSdk(): Promise<void> {
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise((resolve, reject) => {
    if (window.Spotify) {
      resolve();
      return;
    }
    const tag = document.createElement("script");
    tag.src = "https://sdk.scdn.co/spotify-player.js";
    tag.async = true;
    tag.onload = () => resolve();
    tag.onerror = () => reject(new Error("Spotify SDK failed to load"));
    document.body.appendChild(tag);
  });
  return scriptPromise;
}

async function fetchPlayerToken(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/integrations/spotify/token`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Spotify not connected");
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

export async function ensureSpotifyDevice(): Promise<string> {
  if (deviceId) return deviceId;
  if (readyPromise) return readyPromise;

  readyPromise = (async () => {
    await loadSdk();
    await new Promise<void>((resolve) => {
      window.onSpotifyWebPlaybackSDKReady = () => resolve();
      if (window.Spotify) resolve();
    });
    if (!window.Spotify) throw new Error("Spotify SDK unavailable");

    player = new window.Spotify.Player({
      name: "GreenTube Web",
      getOAuthToken: (cb) => {
        void fetchPlayerToken().then(cb).catch(() => cb(""));
      },
      volume: 0.8,
    });

    await new Promise<string>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error("Spotify player timeout")), 15000);
      player!.addListener("ready", ({ device_id }) => {
        window.clearTimeout(timeout);
        if (!device_id) {
          reject(new Error("No Spotify device"));
          return;
        }
        deviceId = device_id;
        resolve(device_id);
      });
      player!.addListener("not_ready", () => {
        window.clearTimeout(timeout);
        reject(new Error("Spotify device not ready"));
      });
      void player!.connect();
    });

    return deviceId!;
  })();

  return readyPromise;
}

export async function playSpotifyUri(uri: string): Promise<void> {
  const dev = await ensureSpotifyDevice();
  const token = await fetchPlayerToken();
  const res = await fetch(
    `https://api.spotify.com/v1/me/player/play?device_id=${encodeURIComponent(dev)}`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ uris: [uri] }),
    },
  );
  if (res.status === 204 || res.ok) return;
  if (res.status === 403) {
    throw new Error("Spotify Premium is required for full playback in GreenTube.");
  }
  const text = await res.text();
  throw new Error(text || `Spotify play failed (${res.status})`);
}

export async function pauseSpotify(): Promise<void> {
  const token = await fetchPlayerToken();
  await fetch("https://api.spotify.com/v1/me/player/pause", {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function resumeSpotify(): Promise<void> {
  const token = await fetchPlayerToken();
  const res = await fetch("https://api.spotify.com/v1/me/player/play", {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 403) {
    throw new Error("Spotify Premium is required for full playback in GreenTube.");
  }
}

export async function seekSpotify(positionMs: number): Promise<void> {
  const token = await fetchPlayerToken();
  await fetch(
    `https://api.spotify.com/v1/me/player/seek?position_ms=${Math.max(0, Math.floor(positionMs))}`,
    {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
    },
  );
}

export function pollSpotifyPlayback(
  onTick: (data: { positionMs: number; durationMs: number; playing: boolean }) => void,
  onEnded: () => void,
): () => void {
  let wasPlaying = false;
  const id = window.setInterval(() => {
    void (async () => {
      try {
        const token = await fetchPlayerToken();
        const res = await fetch("https://api.spotify.com/v1/me/player", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.status === 204) return;
        if (!res.ok) return;
        const data = (await res.json()) as {
          is_playing?: boolean;
          progress_ms?: number;
          item?: { duration_ms?: number };
        };
        const playing = Boolean(data.is_playing);
        const positionMs = data.progress_ms ?? 0;
        const durationMs = data.item?.duration_ms ?? 0;
        onTick({ positionMs, durationMs, playing });
        if (
          wasPlaying &&
          !playing &&
          durationMs > 0 &&
          positionMs >= Math.max(0, durationMs - 2500)
        ) {
          onEnded();
        }
        wasPlaying = playing;
      } catch {
        /* token or network */
      }
    })();
  }, 1000);
  return () => window.clearInterval(id);
}

export async function resolveSpotifyUri(title: string, artist: string): Promise<string | null> {
  try {
    const params = new URLSearchParams({ title, artist });
    const res = await fetch(`${API_BASE}/api/integrations/spotify/track-uri?${params}`, {
      credentials: "include",
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { uri?: string };
    return data.uri ?? null;
  } catch {
    return null;
  }
}

export async function spotifyStatus(): Promise<{ configured: boolean; connected: boolean }> {
  try {
    const res = await fetch(`${API_BASE}/api/integrations/spotify/status`, {
      credentials: "include",
    });
    if (!res.ok) return { configured: false, connected: false };
    return res.json() as Promise<{ configured: boolean; connected: boolean }>;
  } catch {
    return { configured: false, connected: false };
  }
}
