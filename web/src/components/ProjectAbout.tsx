import type { AuditLogEntryResponse, ProjectMemberDetailResponse } from "../api/client";
import ProjectTimeline from "./ProjectTimeline";

interface ProjectAboutProps {
  description: string | null;
  members: ProjectMemberDetailResponse[];
  timeline: AuditLogEntryResponse[];
}

function MemberAvatar({ email }: { email: string }) {
  return (
    <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-ember-500 text-xs font-semibold text-white">
      {email.charAt(0).toUpperCase()}
    </span>
  );
}

export default function ProjectAbout({ description, members, timeline }: ProjectAboutProps) {
  return (
    <aside className="w-full flex-shrink-0 space-y-5 lg:w-72">
      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-100">About</h2>
        <p className="text-sm text-slate-400">
          {description || "No description yet."}
        </p>
        <a
          href="#timeline"
          className="mt-3 inline-block text-sm text-ember-400 transition-colors hover:text-ember-300"
        >
          Activity
        </a>
      </div>

      <div className="border-t border-ink-800 pt-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-100">
          Contributors <span className="text-slate-500">{members.length}</span>
        </h2>
        <ul className="space-y-2">
          {members.map((member) => (
            <li key={member.user_id} className="flex items-center gap-2 text-sm">
              <MemberAvatar email={member.email} />
              <span className="truncate text-slate-300">{member.full_name}</span>
              <span className="ml-auto flex-shrink-0 rounded-full bg-ink-800 px-2 py-0.5 text-xs text-slate-500">
                {member.project_role}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="border-t border-ink-800 pt-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-100">Deliverables</h2>
        <p className="text-sm text-slate-500" title="Coming soon">
          No deliverables published.{" "}
          <span className="text-slate-600">Coming in Phase 3.</span>
        </p>
      </div>

      <div id="timeline" className="border-t border-ink-800 pt-4">
        <ProjectTimeline entries={timeline} />
      </div>
    </aside>
  );
}
