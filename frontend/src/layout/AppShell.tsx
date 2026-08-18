import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { Icon, type IconName } from '../components/Icon';

const navigation: Array<{
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
  preview?: boolean;
}> = [
  { to: '/', label: 'Overview', icon: 'dashboard', end: true },
  { to: '/scans/new', label: 'New domain scan', icon: 'scan' },
  { to: '/identities', label: 'Identity cases', icon: 'identity', preview: true },
  { to: '/files', label: 'File lab', icon: 'file' },
  { to: '/graph', label: 'Exposure graph', icon: 'graph' },
  { to: '/evidence', label: 'Evidence', icon: 'evidence' },
  { to: '/incidents', label: 'Incidents', icon: 'incident' },
  { to: '/monitoring', label: 'Monitoring', icon: 'monitoring' },
  { to: '/alerts', label: 'Alerts', icon: 'alert', preview: true },
  { to: '/reports', label: 'Reports', icon: 'report', preview: true },
  { to: '/settings', label: 'Settings', icon: 'settings' },
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
        <NavLink to="/" className="wordmark" aria-label="Tracynth home">
          <span className="brand-mark" aria-hidden="true">
            T
          </span>
          Tracynth
        </NavLink>
        <button
          className="menu-button"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <Icon name={menuOpen ? 'close' : 'menu'} size={17} />
          <span>{menuOpen ? 'Close' : 'Menu'}</span>
        </button>
      </header>
      {menuOpen ? (
        <button
          className="sidebar-scrim"
          type="button"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}
      <aside className={`sidebar ${menuOpen ? 'sidebar--open' : ''}`}>
        <NavLink to="/" className="wordmark" aria-label="Tracynth overview">
          <span className="brand-mark" aria-hidden="true">
            T
          </span>
          <span>Tracynth</span>
        </NavLink>
        <p className="workspace-label">Private workspace</p>
        <nav id="primary-navigation" aria-label="Primary navigation">
          {navigation.map(({ to, label, icon, end, preview }) => {
            const content = (
              <>
                <span className="nav-link__icon">
                  <Icon name={icon} size={17} />
                </span>
                <span className="nav-link__label">{label}</span>
                {preview ? <span className="nav-link__badge">Soon</span> : null}
              </>
            );
            return preview ? (
              <span className="nav-link nav-link--disabled" aria-disabled="true" key={to}>
                {content}
              </span>
            ) : (
              <NavLink
                key={to}
                to={to}
                end={end}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}
              >
                {content}
              </NavLink>
            );
          })}
        </nav>
        <div className="account-block">
          <div className="avatar" aria-hidden="true">
            {user?.username.slice(0, 1).toUpperCase()}
          </div>
          <div>
            <strong>{user?.username}</strong>
            <span>Operator</span>
          </div>
          <button
            className="account-signout"
            type="button"
            onClick={() => void handleSignOut()}
            disabled={signingOut}
            aria-label="Sign out"
            title="Sign out"
          >
            {signingOut ? <span>…</span> : <Icon name="logout" size={16} />}
          </button>
        </div>
      </aside>
      <main id="main-content" className="main-content" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
