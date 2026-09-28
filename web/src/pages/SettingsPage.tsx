import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  addProjectMember,
  getProject,
  listMemberCandidates,
  listProjectMembers,
  removeProjectMember,
  type ProjectMemberDetailResponse,
  type ProjectResponse,
  type UserSummaryResponse,
} from "../api/client";
import { deleteIssue, listProjectIssues, type IssueResponse } from "../api/client_issues";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { PriorityBadge, StatusBadge } from "../components/IssueBadges";
import ProjectTabs from "../components/ProjectTabs";
import { TrashIcon } from "../components/icons";

export default function SettingsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [issues, setIssues] = useState<IssueResponse[]>([]);
  const [members, setMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [candidates, setCandidates] = useState<UserSummaryResponse[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, issueData, memberData, candidateData] = await Promise.all([
        getProject(token, projectId),
        listProjectIssues(token, projectId),
        listProjectMembers(token, projectId),
        listMemberCandidates(token, projectId),
      ]);
      setProject(projectData);
      setIssues(issueData);
      setMembers(memberData);
      setCandidates(candidateData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    }
  }

  async function handleDeleteIssue(issue: IssueResponse) {
    if (!token) return;
    if (!window.confirm(`Delete "${issue.title}"? This can't be undone.`)) return;
    try {
      await deleteIssue(token, issue.id);
      setIssues((current) => current.filter((i) => i.id !== issue.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete issue");
    }
  }

  async function handleAddMember() {
    if (!token || !projectId || !selectedCandidateId) return;
    try {
      await addProjectMember(token, projectId, selectedCandidateId);
      const candidate = candidates.find((c) => c.id === selectedCandidateId);
      setSelectedCandidateId("");
      setCandidates((current) => current.filter((c) => c.id !== selectedCandidateId));
      if (candidate) {
        setMembers((current) => [
          ...current,
          {
            project_id: projectId,
            user_id: candidate.id,
            project_role: "contributor",
            added_at: new Date().toISOString(),
            email: candidate.email,
            full_name: candidate.full_name,
          },
        ]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add member");
    }
  }

  async function handleRemoveMember(member: ProjectMemberDetailResponse) {
    if (!token || !projectId) return;
    if (!window.confirm(`Remove ${member.full_name} from this project?`)) return;
    try {
      await removeProjectMember(token, projectId, member.user_id);
      setMembers((current) => current.filter((m) => m.user_id !== member.user_id));
      setCandidates((current) => [
        ...current,
        { id: member.user_id, email: member.email, full_name: member.full_name },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove member");
    }
  }

  if (!project) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />

      <div className="mx-auto max-w-5xl space-y-4 p-6">
        {error && <p className="text-sm text-red-400">{error}</p>}

        <section>
          <h2 className="mb-1 text-sm font-semibold text-slate-100">Members</h2>
          <p className="mb-3 text-xs text-slate-500">
            Only members of this project can be assigned activities in Schedule and Kanban.
          </p>
          <div className="divide-y divide-ink-800 rounded-md border border-ink-800 bg-ink-900">
            {members.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">No members added yet.</p>
            ) : (
              members.map((member) => (
                <div
                  key={member.user_id}
                  className="flex flex-wrap items-center gap-2 p-3 text-sm transition-colors hover:bg-ink-800"
                >
                  <span className="text-slate-100">{member.full_name}</span>
                  <span className="text-xs text-slate-500">{member.email}</span>
                  <span className="rounded-full bg-ink-800 px-2 py-0.5 text-[11px] uppercase text-slate-400">
                    {member.project_role}
                  </span>
                  <button
                    onClick={() => void handleRemoveMember(member)}
                    title="Remove member"
                    className="ml-auto text-slate-600 hover:text-red-400"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              ))
            )}
          </div>
          <div className="mt-3 flex items-center gap-2">
            <select
              value={selectedCandidateId}
              onChange={(e) => setSelectedCandidateId(e.target.value)}
              className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            >
              <option value="">
                {candidates.length === 0 ? "No users available to add" : "Select a user…"}
              </option>
              {candidates.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.full_name} ({candidate.email})
                </option>
              ))}
            </select>
            <button
              onClick={() => void handleAddMember()}
              disabled={!selectedCandidateId}
              className="rounded-md bg-ember-500 px-2.5 py-1.5 text-sm font-medium text-white hover:bg-ember-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Add member
            </button>
          </div>
        </section>

        <section>
          <h2 className="mb-1 text-sm font-semibold text-slate-100">Issues</h2>
          <p className="mb-3 text-xs text-slate-500">
            Deleting an issue removes its comments, labels, and history. Subtasks are kept and
            un-linked from their parent rather than deleted.
          </p>
          <div className="divide-y divide-ink-800 rounded-md border border-ink-800 bg-ink-900">
            {issues.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">No issues in this project yet.</p>
            ) : (
              issues.map((issue) => (
                <div
                  key={issue.id}
                  className="flex flex-wrap items-center gap-2 p-3 text-sm transition-colors hover:bg-ink-800"
                >
                  <StatusBadge status={issue.status} />
                  <Link
                    to={`/projects/${projectId}/issues/${issue.id}`}
                    className="text-slate-100 hover:text-ember-400 hover:underline"
                  >
                    {issue.title}
                  </Link>
                  <PriorityBadge priority={issue.priority} />
                  <button
                    onClick={() => void handleDeleteIssue(issue)}
                    title="Delete issue"
                    className="ml-auto text-slate-600 hover:text-red-400"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
