import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <main className="centered not-found">
      <p className="eyebrow">404</p>
      <h1>That trail goes cold.</h1>
      <p>The page does not exist or is no longer available.</p>
      <Link className="button" to="/">
        Return to overview
      </Link>
    </main>
  );
}
