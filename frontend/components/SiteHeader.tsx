'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, FolderArchive, ListChecks, Radar } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';

const navItems = [
  { href: '/', label: 'Дашборд', icon: LayoutDashboard },
  { href: '/problems', label: 'Проблемы', icon: ListChecks },
  { href: '/archive', label: 'Архив', icon: FolderArchive },
  { href: '/scraping', label: 'Скрейпинг', icon: Radar },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[color:var(--card)/0.75] backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-cyan-500 to-emerald-500" />
          <div>
            <p className="title-display text-sm font-semibold tracking-wide text-[var(--text)]">
              Startup Ideas Collector
            </p>
            <p className="text-xs text-[var(--muted)]">AI Discovery Workspace</p>
          </div>
        </div>

        <nav className="hidden items-center gap-2 md:flex">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== '/' && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition ${
                  active
                    ? 'bg-[var(--accent-soft)] text-[var(--text)]'
                    : 'text-[var(--muted)] hover:bg-[var(--card-2)] hover:text-[var(--text)]'
                }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
