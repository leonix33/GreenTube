"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { genreGradient } from "@/lib/genres";
import { GenreTrackList } from "@/components/catalog/GenreTrackList";

type GenreTracksResponse = {
  slug: string;
  name: string;
};

export function GenreDetail({ slug }: { slug: string }) {
  const [name, setName] = useState(
    slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
  );

  useEffect(() => {
    let cancelled = false;
    apiGet<GenreTracksResponse>(`/api/genres/${encodeURIComponent(slug)}/tracks`)
      .then((data) => {
        if (!cancelled) setName(data.name);
      })
      .catch(() => {
        /* GenreTrackList surfaces errors */
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  return (
    <div className="space-y-6 pb-4">
      <div
        className={`rounded-lg bg-gradient-to-br px-6 py-8 ring-1 ring-white/5 ${genreGradient(slug)}`}
      >
        <Link
          href="/explore"
          className="text-xs font-medium uppercase tracking-wide text-white/70 hover:text-white"
        >
          ← All genres
        </Link>
        <h1 className="mt-3 font-display text-3xl text-white md:text-4xl">{name}</h1>
        <p className="mt-2 text-sm text-white/75">Tracks tagged with {slug}</p>
      </div>
      <GenreTrackList slug={slug} />
    </div>
  );
}
