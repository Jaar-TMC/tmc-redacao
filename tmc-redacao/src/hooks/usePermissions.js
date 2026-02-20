import { useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { ROLE_PERMISSIONS, PERMISSIONS } from '../constants/permissions';

export default function usePermissions() {
  const { user } = useAuth();

  return useMemo(() => {
    const role = user?.role || 'user';
    const perms = ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS.user;
    const hasPermission = (perm) => perms.includes(perm);

    return {
      user,
      role,
      isAdmin: role === 'admin',
      hasPermission,
      canAccessSettings: hasPermission(PERMISSIONS.ACCESS_SETTINGS),
      canViewAdvancedMode: hasPermission(PERMISSIONS.VIEW_ADVANCED_MODE),
      canManageUsers: hasPermission(PERMISSIONS.MANAGE_USERS),
    };
  }, [user]);
}
