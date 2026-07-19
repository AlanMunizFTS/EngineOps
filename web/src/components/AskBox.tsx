import { ChevronDownIcon, SendIcon } from "./icons";

const QUICK_ACTIONS = ["Agent", "Create issue", "Write code", "Git", "Pull requests"];

function DropdownButton({ label }: { label: string }) {
  return (
    <button
      disabled
      title="Coming soon"
      className="flex cursor-not-allowed items-center gap-1 rounded-lg border border-ink-700 bg-ink-800 px-3 py-1.5 text-sm text-slate-500"
    >
      {label}
      <ChevronDownIcon />
    </button>
  );
}

export default function AskBox() {
  return (
    <div className="space-y-3">
      <div className="rounded-2xl border border-ink-800 bg-ink-900 p-4 shadow-lg shadow-black/20">
        <div className="flex items-center justify-between gap-3">
          <input
            disabled
            title="Coming soon"
            placeholder="Ask anything or type @ to add context"
            className="w-full cursor-not-allowed bg-transparent text-sm text-slate-500 placeholder-slate-500 outline-none"
          />
          <span className="flex-shrink-0 rounded-full bg-ink-700 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">
            Coming soon
          </span>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <DropdownButton label="Ask" />
          <DropdownButton label="All projects" />
          <button
            disabled
            title="Coming soon"
            className="cursor-not-allowed rounded-lg border border-ink-700 bg-ink-800 px-2.5 py-1.5 text-sm text-slate-500"
          >
            +
          </button>
          <div className="ml-auto flex items-center gap-2">
            <DropdownButton label="Auto" />
            <button
              disabled
              title="Coming soon"
              className="flex h-8 w-8 cursor-not-allowed items-center justify-center rounded-lg bg-ink-700 text-slate-500"
            >
              <SendIcon />
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((label) => (
          <button
            key={label}
            disabled
            title="Coming soon"
            className="cursor-not-allowed rounded-lg border border-ink-700 bg-ink-850 px-3 py-1.5 text-sm text-slate-500"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
