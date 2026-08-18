import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { ErrorState, LoadingState } from '../components/AsyncState';

export function ProtectedRoute() {
  const { user, loading, error, refresh } = useAuth();
  const location = useLocation();
  if (loading)
    return (
      <main className="centered">
        <LoadingState label="Checking session" />
      </main>
    );
  if (error)
    return (
      <main className="centered">
        <ErrorState error={error} onRetry={() => void refresh()} />
      </main>
    );
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return <Outlet />;
}
