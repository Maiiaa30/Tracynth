import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { displayError } from '../lib/api';

export function LoginPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signIn(username.trim(), password);
      const state = location.state as { from?: { pathname?: string } } | null;
      void navigate(state?.from?.pathname ?? '/', { replace: true });
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-layout">
      <section className="login-intro">
        <div className="wordmark wordmark--large">
          <span className="brand-mark" aria-hidden="true">
            T
          </span>
          Tracynth
        </div>
        <p className="eyebrow">Private intelligence workspace</p>
        <h1>
          Trace exposure.
          <br />
          Preserve the evidence.
        </h1>
        <p>
          A controlled workspace for domain reconnaissance, identity correlation, and
          evidence-backed investigation.
        </p>
      </section>
      <section className="login-card" aria-labelledby="login-title">
        <div>
          <p className="eyebrow">Operator access</p>
          <h2 id="login-title">Sign in</h2>
          <p>Use the operator account configured by your administrator.</p>
        </div>
        <form onSubmit={(event) => void submit(event)}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            name="username"
            autoComplete="username"
            required
            autoFocus
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
          <button className="button" type="submit" disabled={submitting || !username || !password}>
            {submitting ? 'Signing in…' : 'Sign in securely'}
          </button>
        </form>
        <p className="security-note">
          Session cookies and CSRF protection are enforced by the server.
        </p>
      </section>
    </main>
  );
}
