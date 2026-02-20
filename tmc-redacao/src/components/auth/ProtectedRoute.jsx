import PropTypes from 'prop-types';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import usePermissions from '../../hooks/usePermissions';
import AuthLoadingScreen from './AuthLoadingScreen';
import AccessDenied from './AccessDenied';

function ProtectedRoute({ children, permission }) {
  const { isAuthenticated, isLoading } = useAuth();
  const { hasPermission } = usePermissions();

  if (isLoading) return <AuthLoadingScreen />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (permission && !hasPermission(permission)) return <AccessDenied />;

  return children;
}

ProtectedRoute.propTypes = {
  children: PropTypes.node.isRequired,
  permission: PropTypes.string,
};

export default ProtectedRoute;
