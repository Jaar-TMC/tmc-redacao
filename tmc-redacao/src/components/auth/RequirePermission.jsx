import PropTypes from 'prop-types';
import usePermissions from '../../hooks/usePermissions';

function RequirePermission({ children, permission }) {
  const { hasPermission } = usePermissions();
  if (!hasPermission(permission)) return null;
  return children;
}

RequirePermission.propTypes = {
  children: PropTypes.node.isRequired,
  permission: PropTypes.string.isRequired,
};

export default RequirePermission;
