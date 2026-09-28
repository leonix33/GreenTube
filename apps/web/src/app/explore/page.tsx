import { GenreGrid } from "@/components/catalog/GenreGrid";

export default function ExplorePage() {
  return (
    <div className="space-y-6 pb-4">
      <div>
        <h1 className="font-display text-3xl text-white">Explore</h1>
        <p className="mt-2 max-w-2xl text-sm text-gt-muted">
          Browse by genre — Afrobeats, Hip-Hop, Jazz, House, K-Pop, and more. Demo tracks
          play through the open provider; empty genres are ready for catalog ingest.
        </p>
      </div>
      <GenreGrid />
    </div>
  );
}
