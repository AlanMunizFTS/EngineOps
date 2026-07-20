import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { ProjectResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import Brand from "./Brand";
import {
  AiBadgeIcon,
  BookIcon,
  ChevronDownIcon,
  ClockIcon,
  GitCompareIcon,
  InboxIcon,
  MenuIcon,
  PlusIcon,
  SearchIcon,
} from "./icons";

interface TopBarProps {
  projects: ProjectResponse[];
  onToggleSidebar?: () => void;
  breadcrumb?: string;
}

function ComingSoonIconButton({
  icon: Icon,
  label,
  withChevron,
}: {
  icon: (props: { className?: string }) => JSX.Element;
  label: string;
  withChevron?: boolean;
}) {
  return (
    <button
      disabled
      title={`${label} — Coming soon`}
      aria-label={label}
      className="flex cursor-not-allowed items-center gap-0.5 rounded-md p-1.5 text-slate-500 opacity-70"
    >
      <Icon className="h-5 w-5" />
      {withChevron && <ChevronDownIcon className="h-3.5 w-3.5" />}
    </button>
  );
}

export default function TopBar({ projects, onToggleSidebar, breadcrumb }: TopBarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const isTyping = target?.tagName === "INPUT" || target?.tagName === "TEXTAREA";
      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const matches =
    query.trim().length > 0
      ? projects.filter((p) => p.name.toLowerCase().includes(query.toLowerCase())).slice(0, 6)
      : [];

  function goTo(projectId: string) {
    setQuery("");
    setIsFocused(false);
    navigate(`/projects/${projectId}`);
  }

  return (
    <header className="flex items-center gap-3 border-b border-ink-800 bg-ink-900/70 px-4 py-3 backdrop-blur">
      {onToggleSidebar && (
        <button
          onClick={onToggleSidebar}
          className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-ink-800 hover:text-slate-100"
          aria-label="Toggle sidebar"
        >
          <MenuIcon />
        </button>
      )}

      <Link to="/projects" className="flex flex-shrink-0 items-center gap-1.5">
        <Brand />
        {breadcrumb && (
          <>
            <span className="text-slate-600">/</span>
            <span className="text-sm font-semibold text-slate-100">{breadcrumb}</span>
          </>
        )}
      </Link>

      <div className="relative ml-2 w-full max-w-md">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 100)}
          placeholder="Type / to search"
          className="w-full rounded-lg border border-ink-700 bg-ink-800 py-1.5 pl-9 pr-3 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
        />
        {isFocused && matches.length > 0 && (
          <ul className="absolute left-0 right-0 top-full z-10 mt-1 overflow-hidden rounded-lg border border-ink-700 bg-ink-850 shadow-xl shadow-black/40">
            {matches.map((project) => (
              <li key={project.id}>
                <button
                  onClick={() => goTo(project.id)}
                  className="block w-full truncate px-3 py-2 text-left text-sm text-slate-200 hover:bg-ink-800"
                >
                  {project.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="ml-auto flex items-center gap-1">
        <ComingSoonIconButton icon={AiBadgeIcon} label="AI assistant" withChevron />

        <button
          onClick={() => navigate("/projects?create=1")}
          className="flex items-center gap-0.5 rounded-md p-1.5 text-slate-400 transition-colors hover:bg-ink-800 hover:text-slate-100"
          aria-label="New project"
        >
          <PlusIcon className="h-5 w-5" />
          <ChevronDownIcon className="h-3.5 w-3.5" />
        </button>

        <ComingSoonIconButton icon={ClockIcon} label="History" />
        <ComingSoonIconButton icon={GitCompareIcon} label="Compare" />
        <ComingSoonIconButton icon={BookIcon} label="Docs" />
        <ComingSoonIconButton icon={InboxIcon} label="Notifications" />

        <div ref={menuRef} className="relative ml-1">
          <button
            onClick={() => setIsMenuOpen((prev) => !prev)}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-ember-500 text-sm font-semibold text-white"
            aria-label="Account menu"
          >
            {user?.email.charAt(0).toUpperCase()}
          </button>
          {isMenuOpen && (
            <div className="absolute right-0 top-full z-10 mt-2 w-56 overflow-hidden rounded-lg border border-ink-700 bg-ink-850 shadow-xl shadow-black/40">
              <p className="truncate border-b border-ink-700 px-3 py-2 text-sm text-slate-300">
                {user?.email}
              </p>
              <button
                onClick={logout}
                className="block w-full px-3 py-2 text-left text-sm text-slate-300 hover:bg-ink-800"
              >
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
