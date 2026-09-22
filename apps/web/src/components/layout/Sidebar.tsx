"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/explore", label: "Explore" },
  { href: "/library", label: "Library" },
  { href: "/playlists", label: "Playlists" },
  { href: "/liked", label: "Liked" },
  { href: "/downloads", label: "Downloads" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 shrink-0 flex-col gap-6 border-r border-gt-border bg-black/40 px-4 py-5 backdrop-blur-md">
      <Link href="/" className="group flex items-center gap-2 px-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-gt-green text-sm font-bold text-black">
          GT
        </span>
        <span className="font-display text-xl tracking-tight text-white group-hover:text-gt-green">
          GreenTube
        </span>
      </Link>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-gt-elevated text-white"
                  : "text-gt-muted hover:bg-white/5 hover:text-white",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <button
        type="button"
        className="rounded-md border border-dashed border-gt-border px-3 py-2 text-left text-sm text-gt-muted transition hover:border-gt-green/50 hover:text-white"
      >
        + Playlist
      </button>
    </aside>
  );
}
