"use client";

export function TopBar() {
  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b border-gt-border bg-black/30 px-6 backdrop-blur-md">
      <div className="relative flex-1">
        <label htmlFor="gt-search" className="sr-only">
          Search
        </label>
        <input
          id="gt-search"
          type="search"
          placeholder="Search songs, albums, artists..."
          className="w-full max-w-xl rounded-full border border-gt-border bg-gt-elevated/80 px-4 py-2 text-sm text-white placeholder:text-gt-muted outline-none ring-gt-green/40 transition focus:ring-2"
        />
      </div>
      <button
        type="button"
        className="rounded-full bg-gt-elevated px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10"
      >
        Profile
      </button>
    </header>
  );
}
