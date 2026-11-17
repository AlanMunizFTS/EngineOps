interface DailyRepeatFieldProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  disabledReason?: string;
}

export default function DailyRepeatField({
  checked,
  onChange,
  disabled = false,
  disabledReason,
}: DailyRepeatFieldProps) {
  return (
    <label className={`flex items-start gap-2 rounded-md border border-ink-700 bg-ink-800/60 px-3 py-2 ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}>
      <input
        aria-label="Repeat every day"
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5"
      />
      <span>
        <span className="block text-sm text-slate-200">Repeat every day</span>
        <span className="block text-xs text-slate-500">
          {disabled && disabledReason
            ? disabledReason
            : "Completing it creates the next occurrence for the following day."}
        </span>
      </span>
    </label>
  );
}
