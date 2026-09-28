import Link from "next/link";

const CURATED = [
  {
    href: "/playlists/liked-music",
    title: "Liked Music · Part 1",
    subtitle: "49 tracks — Davido, ODUMODUBLVCK, Wizkid, Tems, Omah Lay…",
    gradient: "from-rose-500/60 via-fuchsia-950/50 to-gt-charcoal",
  },
  {
    href: "/playlists/major-afrobeats",
    title: "Major Afrobeats",
    subtitle: "Davido · Burna Boy · Wizkid · Asake · Rema · Odumodublvck",
    gradient: "from-amber-500/60 via-orange-900/50 to-gt-charcoal",
  },
];

export default function PlaylistsPage() {
  return (
    <div className="space-y-8 pb-4">
      <div>
        <h1 className="font-display text-3xl text-white">Playlists</h1>
        <p className="mt-1 text-sm text-gt-muted">
          Curated mixes from your catalog. Custom playlists coming with library sync.
        </p>
      </div>

      <section>
        <p className="gt-section-label mb-3">Made for you</p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CURATED.map((p) => (
            <Link
              key={p.href}
              href={p.href}
              className="group overflow-hidden rounded-md ring-1 ring-white/5 transition hover:-translate-y-0.5"
            >
              <div className={`h-32 bg-gradient-to-br ${p.gradient} p-4`}>
                <p className="font-display text-xl text-white">{p.title}</p>
              </div>
              <div className="bg-gt-elevated px-4 py-3">
                <p className="text-xs text-gt-muted">{p.subtitle}</p>
                <p className="mt-2 text-xs font-medium text-gt-green group-hover:underline">
                  Open playlist →
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
