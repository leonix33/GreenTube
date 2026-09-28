export type Genre = {
  slug: string;
  name: string;
  track_count: number;
};

export const GENRE_GRADIENTS: Record<string, string> = {
  afrobeats: "from-amber-500/70 via-orange-800/60 to-gt-charcoal",
  "hip-hop": "from-violet-600/70 via-fuchsia-900/50 to-gt-charcoal",
  rnb: "from-rose-500/60 via-purple-900/50 to-gt-charcoal",
  pop: "from-pink-500/60 via-indigo-900/50 to-gt-charcoal",
  rock: "from-red-700/70 via-stone-900/60 to-gt-charcoal",
  indie: "from-teal-600/60 via-slate-900/50 to-gt-charcoal",
  electronic: "from-cyan-500/60 via-blue-950/60 to-gt-charcoal",
  house: "from-sky-500/70 via-indigo-950/60 to-gt-charcoal",
  techno: "from-blue-600/70 via-violet-950/60 to-gt-charcoal",
  jazz: "from-amber-700/60 via-stone-900/60 to-gt-charcoal",
  blues: "from-indigo-700/60 via-slate-950/60 to-gt-charcoal",
  soul: "from-orange-600/60 via-rose-950/50 to-gt-charcoal",
  funk: "from-yellow-500/70 via-orange-950/60 to-gt-charcoal",
  classical: "from-stone-400/50 via-zinc-900/60 to-gt-charcoal",
  ambient: "from-emerald-700/50 via-teal-950/60 to-gt-charcoal",
  chill: "from-teal-500/50 via-cyan-950/50 to-gt-charcoal",
  focus: "from-gt-green/50 via-emerald-950/60 to-gt-charcoal",
  latin: "from-red-500/70 via-orange-950/60 to-gt-charcoal",
  reggae: "from-lime-600/60 via-green-950/60 to-gt-charcoal",
  dancehall: "from-yellow-600/70 via-green-950/60 to-gt-charcoal",
  country: "from-amber-600/60 via-yellow-950/50 to-gt-charcoal",
  folk: "from-lime-700/50 via-emerald-950/50 to-gt-charcoal",
  gospel: "from-violet-500/60 via-purple-950/60 to-gt-charcoal",
  metal: "from-zinc-500/60 via-neutral-950/70 to-gt-charcoal",
  punk: "from-fuchsia-600/70 via-rose-950/60 to-gt-charcoal",
  "k-pop": "from-pink-500/70 via-violet-950/60 to-gt-charcoal",
  world: "from-orange-500/60 via-amber-950/50 to-gt-charcoal",
  soundtrack: "from-slate-500/60 via-slate-950/60 to-gt-charcoal",
  workout: "from-red-600/70 via-orange-950/60 to-gt-charcoal",
  "late-night": "from-indigo-800/70 via-purple-950/70 to-black",
  instrumental: "from-emerald-600/50 via-teal-950/60 to-gt-charcoal",
};

export function genreGradient(slug: string): string {
  return GENRE_GRADIENTS[slug] ?? "from-gt-green/40 via-teal-900/50 to-gt-charcoal";
}
