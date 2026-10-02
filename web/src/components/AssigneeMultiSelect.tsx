import type { ProjectMemberDetailResponse } from "../api/client";

export default function AssigneeMultiSelect({
  members,
  selectedIds,
  onChange,
  label = "Assignees",
}: {
  members: ProjectMemberDetailResponse[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  label?: string;
}) {
  function toggle(userId: string, checked: boolean) {
    onChange(
      checked
        ? [...selectedIds, userId]
        : selectedIds.filter((selectedId) => selectedId !== userId),
    );
  }

  return (
    <fieldset>
      <legend className="mb-1 block text-xs font-medium text-slate-400">{label}</legend>
      <div className="max-h-36 space-y-1 overflow-y-auto rounded-md border border-ink-700 bg-ink-800 p-2">
        {members.length === 0 ? (
          <p className="px-1 py-1 text-xs text-slate-500">No project members available.</p>
        ) : members.map((member) => (
          <label key={member.user_id} className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm text-slate-200 hover:bg-ink-700">
            <input
              type="checkbox"
              checked={selectedIds.includes(member.user_id)}
              onChange={(event) => toggle(member.user_id, event.target.checked)}
              aria-label={member.full_name}
              className="accent-ember-500"
            />
            <span className="truncate">{member.full_name}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
