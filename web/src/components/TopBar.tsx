import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { ProjectResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import Brand from "./Brand";
import { MenuIcon, PlusIcon, SearchIcon } from "./icons";

interface TopBarProps {
  projects: ProjectResponse[];
  onToggleSidebar: () => void;
}

export default function TopBar({ projects, onToggleSidebar }: TopBarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);

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
    <header className="flex items-center gap-4 border-b border-ink-800 bg-ink-900/70 px-4 py-3 backdrop-blur">
      <button
        onClick={onToggleSidebar}
        className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-ink-800 hover:text-slate-100"
        aria-label="Toggle sidebar"
      >
        <MenuIcon />
      </button>

      <Link to="/projects" className="flex-shrink-0">
        <Brand />
      </Link>

      <div className="relative w-full max-w-md">
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

      <button
        onClick={() => navigate("/projects?create=1")}
        className="ml-auto rounded-md p-1.5 text-slate-400 transition-colors hover:bg-ink-800 hover:text-slate-100"
        aria-label="New project"
      >
        <PlusIcon />
      </button>

      <div className="flex items-center gap-3 text-sm text-slate-400">
        <span className="hidden sm:inline">{user?.email}</span>
        <button onClick={logout} className="text-slate-500 transition-colors hover:text-ember-400">
          Log out
        </button>
      </div>
    </header>
  );
}
