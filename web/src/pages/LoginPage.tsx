import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { getCurrentUser, login } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import Brand from "../components/Brand";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { setSession } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const token = await login(email, password);
      const user = await getCurrentUser(token.access_token);
      setSession(token.access_token, user);
      navigate("/projects");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-ink-950">
      <div className="pointer-events-none absolute left-1/2 top-1/3 h-[32rem] w-[32rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-ember-500/10 blur-3xl" />

      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-sm space-y-5 rounded-2xl border border-ink-700 bg-ink-900 p-8 shadow-xl shadow-black/40"
      >
        <div className="space-y-1">
          <Brand />
          <p className="pt-3 text-lg font-semibold text-slate-100">Sign in</p>
          <p className="text-sm text-slate-500">Engineering operations, in one place.</p>
        </div>

        <div className="space-y-3">
          <input
            type="text"
            autoCapitalize="off"
            autoCorrect="off"
            placeholder="Username or email"
            title="Username (e.g. jdoe) or full email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          className="w-full rounded-lg bg-ember-500 py-2 text-sm font-medium text-white transition-colors hover:bg-ember-600"
        >
          Log in
        </button>
      </form>
    </div>
  );
}
