export default function Brand({ subtitle }: { subtitle?: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-7 w-7 items-center justify-center rounded-md bg-ember-500 text-sm font-bold text-white shadow-glow">
        E
      </span>
      <div className="leading-tight">
        <p className="text-sm font-semibold tracking-tight text-slate-100">
          Engine<span className="text-ember-400">Ops</span>
        </p>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
    </div>
  );
}
