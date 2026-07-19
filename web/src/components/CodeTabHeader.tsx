import {
  ChevronDownIcon,
  CodeBracketIcon,
  EyeIcon,
  ForkIcon,
  LockIcon,
  SearchIcon,
  StarIcon,
} from "./icons";

function PillButton({
  icon: Icon,
  label,
  count,
}: {
  icon: (props: { className?: string }) => JSX.Element;
  label: string;
  count: number;
}) {
  return (
    <button
      disabled
      title={`${label} — coming soon`}
      className="flex cursor-not-allowed items-center gap-1.5 rounded-l-md rounded-r-none border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300 opacity-90 first:rounded-l-md"
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
      <ChevronDownIcon className="h-3 w-3 text-slate-500" />
      <span className="rounded-full bg-ink-800 px-1.5 py-0.5 text-[10px] text-slate-400">
        {count}
      </span>
    </button>
  );
}

export default function CodeTabHeader() {
  return (
    <div className="space-y-3 border-b border-ink-800 px-8 py-4">
      <div className="flex items-center gap-2">
        <span className="flex items-center gap-1 rounded-full bg-ink-800 px-2 py-0.5 text-xs font-medium text-slate-400">
          <LockIcon />
          Internal
        </span>
        <div className="ml-auto flex items-center gap-2">
          <PillButton icon={EyeIcon} label="Watch" count={0} />
          <PillButton icon={ForkIcon} label="Fork" count={0} />
          <PillButton icon={StarIcon} label="Star" count={0} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          disabled
          title="Branches — coming soon"
          className="flex cursor-not-allowed items-center gap-1.5 rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300"
        >
          <CodeBracketIcon className="h-3.5 w-3.5" />
          main
          <ChevronDownIcon className="h-3 w-3 text-slate-500" />
        </button>
        <span className="text-xs text-slate-500">0 Branches</span>
        <span className="text-xs text-slate-500">0 Tags</span>

        <div className="relative ml-auto w-full max-w-[220px]">
          <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
          <input
            disabled
            placeholder="Go to file"
            title="Coming soon"
            className="w-full cursor-not-allowed rounded-md border border-ink-700 bg-ink-850 py-1 pl-8 pr-2 text-xs text-slate-500 outline-none"
          />
        </div>
        <button
          disabled
          title="Coming soon"
          className="cursor-not-allowed rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300"
        >
          Add file
        </button>
        <button
          disabled
          title="Coming soon"
          className="flex cursor-not-allowed items-center gap-1 rounded-md bg-emerald-600/80 px-2.5 py-1 text-xs font-medium text-white"
        >
          Code
          <ChevronDownIcon className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}
