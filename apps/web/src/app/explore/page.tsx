export default function ExplorePage() {
  return (
    <div className="space-y-4">
      <h1 className="font-display text-3xl text-white">Explore</h1>
      <p className="text-sm text-gt-muted">
        Genres, moods, charts, and new releases will land here after catalog ingestion.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {["Afrobeats", "Focus", "Late Night", "Indie", "Jazz", "Workout"].map(
          (mood) => (
            <div
              key={mood}
              className="rounded-md bg-gt-elevated px-4 py-8 ring-1 ring-white/5"
            >
              <p className="font-display text-xl text-white">{mood}</p>
            </div>
          ),
        )}
      </div>
    </div>
  );
}
