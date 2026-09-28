import { useEffect, useState } from "react";

import {
  createAdminUser,
  createUser,
  deleteAdminUser,
  listAdminUsers,
  updateAdminUser,
  type UserResponse,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { TrashIcon } from "../components/icons";

const AVAILABLE_ROLES = ["admin", "engineer", "viewer"];

export default function AdminUsersPage() {
  const { token, user: currentUser } = useAuth();
  const isAdmin = currentUser?.roles.includes("admin") ?? false;

  const [users, setUsers] = useState<UserResponse[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [makeAdmin, setMakeAdmin] = useState(false);
  const [editingUser, setEditingUser] = useState<UserResponse | null>(null);
  const [editFullName, setEditFullName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editPassword, setEditPassword] = useState("");
  const [editIsActive, setEditIsActive] = useState(true);
  const [editRoles, setEditRoles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && isAdmin) void loadUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isAdmin]);

  async function loadUsers() {
    if (!token) return;
    try {
      setUsers(await listAdminUsers(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    }
  }

  async function handleCreateUser() {
    if (!token || !email.trim() || !password || !fullName.trim()) return;
    try {
      const fields = {
        email: email.trim(),
        password,
        full_name: fullName.trim(),
      };
      if (isAdmin) {
        await createAdminUser(token, { ...fields, is_admin: makeAdmin });
      } else {
        await createUser(token, fields);
      }
      setEmail("");
      setPassword("");
      setFullName("");
      setMakeAdmin(false);
      if (isAdmin) await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    }
  }

  function startEditing(userToEdit: UserResponse) {
    setEditingUser(userToEdit);
    setEditFullName(userToEdit.full_name);
    setEditEmail(userToEdit.email);
    setEditPassword("");
    setEditIsActive(userToEdit.is_active);
    setEditRoles(userToEdit.roles);
    setError(null);
  }

  async function handleUpdateUser() {
    if (!token || !editingUser || !editEmail.trim() || !editFullName.trim()) return;
    try {
      const updated = await updateAdminUser(token, editingUser.id, {
        email: editEmail.trim(),
        full_name: editFullName.trim(),
        ...(editPassword ? { password: editPassword } : {}),
        is_active: editIsActive,
        roles: editRoles,
      });
      setUsers((current) => current.map((user) => (user.id === updated.id ? updated : user)));
      setEditingUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    }
  }

  async function handleDeleteUser(userToDelete: UserResponse) {
    if (!token) return;
    if (!window.confirm(`Delete "${userToDelete.full_name}" (${userToDelete.email})?`)) return;
    try {
      await deleteAdminUser(token, userToDelete.id);
      setUsers((current) => current.filter((u) => u.id !== userToDelete.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete user");
    }
  }

  return (
    <AppShell breadcrumb={isAdmin ? "Admin: Users" : "Create user"}>
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        {error && <p className="text-sm text-red-400">{error}</p>}

        <section className="space-y-2 rounded-md border border-ink-800 bg-ink-900 p-4">
          <h2 className="text-sm font-semibold text-slate-100">Create user</h2>
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              placeholder="Full name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="flex-1 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            />
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            />
            <input
              type="password"
              placeholder="Temporary password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="flex-1 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            />
          </div>
          {isAdmin && (
            <label className="flex items-center gap-1.5 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={makeAdmin}
                onChange={(e) => setMakeAdmin(e.target.checked)}
                className="accent-ember-500"
              />
              Grant admin privileges
            </label>
          )}
          <button
            onClick={handleCreateUser}
            className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
          >
            Create user
          </button>
        </section>

        {isAdmin && (
          <>
            {editingUser && (
              <section className="space-y-3 rounded-md border border-ink-800 bg-ink-900 p-4">
                <h2 className="text-sm font-semibold text-slate-100">
                  Edit {editingUser.full_name}
                </h2>
                <div className="grid gap-2 sm:grid-cols-2">
                  <input
                    type="text"
                    placeholder="Full name"
                    value={editFullName}
                    onChange={(e) => setEditFullName(e.target.value)}
                    className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
                  />
                  <input
                    type="email"
                    placeholder="Email"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
                  />
                  <input
                    type="password"
                    placeholder="New password (optional)"
                    value={editPassword}
                    onChange={(e) => setEditPassword(e.target.value)}
                    className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
                  />
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      checked={editIsActive}
                      onChange={(e) => setEditIsActive(e.target.checked)}
                      disabled={editingUser.id === currentUser?.id}
                      className="accent-ember-500"
                    />
                    Active account
                  </label>
                </div>
                <div className="flex flex-wrap gap-4">
                  {AVAILABLE_ROLES.map((role) => (
                    <label key={role} className="flex items-center gap-1.5 text-xs text-slate-400">
                      <input
                        type="checkbox"
                        checked={editRoles.includes(role)}
                        onChange={(e) =>
                          setEditRoles((current) =>
                            e.target.checked
                              ? [...current, role]
                              : current.filter((item) => item !== role),
                          )
                        }
                        disabled={editingUser.id === currentUser?.id && role === "admin"}
                        className="accent-ember-500"
                      />
                      {role}
                    </label>
                  ))}
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setEditingUser(null)}
                    className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => void handleUpdateUser()}
                    className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-ember-600"
                  >
                    Save changes
                  </button>
                </div>
              </section>
            )}

            <section>
              <h2 className="mb-2 text-sm font-semibold text-slate-100">All users</h2>
              <div className="divide-y divide-ink-800 rounded-md border border-ink-800 bg-ink-900">
                {users.length === 0 ? (
                  <p className="p-4 text-sm text-slate-500">No users yet.</p>
                ) : (
                  users.map((u) => (
                    <div
                      key={u.id}
                      className="flex flex-wrap items-center gap-2 p-3 text-sm transition-colors hover:bg-ink-800"
                    >
                      <span className="text-slate-100">{u.full_name}</span>
                      <span className="text-xs text-slate-500">{u.email}</span>
                      {u.roles.map((role) => (
                        <span
                          key={role}
                          className="rounded-full bg-ember-500/10 px-2 py-0.5 text-[10px] uppercase text-ember-400"
                        >
                          {role}
                        </span>
                      ))}
                      {!u.is_active && (
                        <span className="rounded-full bg-ink-800 px-2 py-0.5 text-[10px] uppercase text-slate-500">
                          inactive
                        </span>
                      )}
                      <div className="ml-auto flex items-center gap-3">
                        <button
                          onClick={() => startEditing(u)}
                          className="text-xs text-slate-400 hover:text-ember-400"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => void handleDeleteUser(u)}
                          disabled={u.id === currentUser?.id}
                          title={u.id === currentUser?.id ? "Cannot delete your own account" : "Delete user"}
                          className="text-slate-600 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-30"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
