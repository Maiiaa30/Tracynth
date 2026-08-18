import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

const navigation = [
  { to: '/', label: 'Overview', glyph: '⌁', end: true },
  { to: '/scans/new', label: 'New domain scan', glyph: '+' },
  { to: '/identities', label: 'Identity cases', glyph: '◎' },
  { to: '/files', label: 'File lab', glyph: '◇' },
  { to: '/graph', label: 'Exposure graph', glyph: '⌘' },
  { to: '/evidence', label: 'Evidence', glyph: '◫' },
  { to: '/incidents', label: 'Incidents', glyph: '!' },
  { to: '/monitoring', label: 'Monitoring', glyph: '↻' },
  { to: '/alerts', label: 'Alerts', glyph: '△' },
  { to: '/reports', label: 'Reports', glyph: '▤' },
  { to: '/settings', label: 'Settings', glyph: '⚙' },
];

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await signOut();
      void navigate('/login', { replace: true });
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="mobile-header">
        <a href="/" className="wordmark" aria-label="Tracynth home">
          <span className="brand-mark" aria-hidden="true">
            T
          </span>
          Tracynth
        </a>
        <button
          className="menu-button"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          Menu
        </button>
      </header>
      <aside className={`sidebar ${menuOpen ? 'sidebar--open' : ''}`}>
        <NavLink to="/" className="wordmark" aria-label="Tracynth overview">
          <span className="brand-mark" aria-hidden="true">
            T
          </span>
          <span>Tracynth</span>
        </NavLink>
        <p className="workspace-label">Private workspace</p>
        <nav id="primary-navigation" aria-label="Primary navigation">
          {navigation.map(({ to, label, glyph, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}
            >
              <span aria-hidden="true">{glyph}</span>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="account-block">
          <div className="avatar" aria-hidden="true">
            {user?.username.slice(0, 1).toUpperCase()}
          </div>
          <div>
            <strong>{user?.username}</strong>
            <span>Operator</span>
          </div>
          <button type="button" onClick={() => void handleSignOut()} disabled={signingOut}>
            {signingOut ? '…' : 'Sign out'}
          </button>
        </div>
      </aside>
      <main id="main-content" className="main-content" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
