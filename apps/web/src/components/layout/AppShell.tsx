"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { MiniPlayer } from "@/components/player/MiniPlayer";
import { PlaybackProvider } from "@/lib/playback";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <PlaybackProvider>
      <div className="flex h-dvh flex-col overflow-hidden">
        <div className="flex min-h-0 flex-1">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <TopBar />
            <main className="flex-1 overflow-y-auto px-6 py-6">{children}</main>
          </div>
        </div>
        <MiniPlayer />
      </div>
    </PlaybackProvider>
  );
}
