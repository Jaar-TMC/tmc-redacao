import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Search, Plus, MoreVertical, Edit2, KeyRound, UserX,
  Shield, User as UserIcon, Mail, Lock, Eye, EyeOff, X,
  RefreshCw, AlertCircle
} from 'lucide-react';
import { getUsers, createUser, updateUser, deactivateUser, resetPassword } from '../../services/userApi';
import { useAuth } from '../../context/AuthContext';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import StatusMessage from '../../components/ui/StatusMessage';
import Skeleton from '../../components/ui/Skeleton';
import Spinner from '../../components/ui/Spinner';

const ITEMS_PER_PAGE = 10;

/**
 * Format a date into a human-readable relative time string in Portuguese.
 * Returns "Nunca" for null/undefined, "Hoje as HH:MM" for today,
 * "Ontem as HH:MM" for yesterday, "Ha X dias" for dates within 30 days,
 * or the full date for older entries.
 */
function formatLastLogin(dateStr) {
  if (!dateStr) return 'Nunca';

  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return 'Nunca';

  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.floor((today - target) / (1000 * 60 * 60 * 24));

  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  if (diffDays === 0) return `Hoje às ${hours}:${minutes}`;
  if (diffDays === 1) return `Ontem às ${hours}:${minutes}`;
  if (diffDays <= 30) return `Há ${diffDays} dias`;

  return date.toLocaleDateString('pt-BR');
}

/**
 * Validate email format with a simple regex.
 */
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * UsuariosPage - Admin user management page
 * Manages user accounts within the TMC editorial system.
 *
 * Features:
 * - List users with search and role filtering
 * - Create / edit user accounts
 * - Reset user passwords
 * - Deactivate user accounts
 * - Pagination
 * - Accessibility-focused with ARIA labels and keyboard navigation
 * - Focus trap for modal dialogs
 */
const UsuariosPage = () => {
  const { user: currentUser } = useAuth();

  // -- Data state --
  const [users, setUsers] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // -- Filters & pagination --
  const [searchInput, setSearchInput] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // -- Create / Edit modal --
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({ name: '', email: '', password: '', role: 'user' });
  const [showPassword, setShowPassword] = useState(false);
  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // -- Reset password modal --
  const [resetModal, setResetModal] = useState({ isOpen: false, user: null });
  const [resetPasswordValue, setResetPasswordValue] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetErrors, setResetErrors] = useState({});
  const [isResetting, setIsResetting] = useState(false);

  // -- Deactivate confirm --
  const [deactivateConfirm, setDeactivateConfirm] = useState({ isOpen: false, user: null });

  // -- Actions dropdown --
  const [openDropdown, setOpenDropdown] = useState(null);

  // -- Status message --
  const [statusMessage, setStatusMessage] = useState({ isVisible: false, type: 'success', message: '' });

  // -- Refs --
  const modalRef = useRef(null);
  const resetModalRef = useRef(null);
  const previousFocusRef = useRef(null);
  const dropdownRefs = useRef({});
  const searchTimeoutRef = useRef(null);

  // Derived
  const totalPages = Math.max(1, Math.ceil(totalUsers / ITEMS_PER_PAGE));

  // ===== Data fetching =====
  const fetchUsers = useCallback(async (page = currentPage, search = searchInput, role = roleFilter) => {
    setIsLoading(true);
    setError(null);
    try {
      const params = { page, limit: ITEMS_PER_PAGE };
      if (search.trim()) params.search = search.trim();
      if (role) params.role = role;
      const response = await getUsers(params);
      setUsers(response.items || response.users || []);
      setTotalUsers(response.total ?? (response.items || response.users || []).length);
    } catch (err) {
      console.error('Error fetching users:', err);
      setError(err.message || 'Erro ao carregar usuários');
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, searchInput, roleFilter]);

  // Initial load
  useEffect(() => {
    fetchUsers(1, '', '');
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  // Refetch on filter/page change (debounce search)
  useEffect(() => {
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(() => {
      fetchUsers(currentPage, searchInput, roleFilter);
    }, 300);
    return () => clearTimeout(searchTimeoutRef.current);
  }, [currentPage, searchInput, roleFilter]);  // eslint-disable-line react-hooks/exhaustive-deps

  const handleRetry = useCallback(() => {
    fetchUsers(currentPage, searchInput, roleFilter);
  }, [fetchUsers, currentPage, searchInput, roleFilter]);

  // ===== Close dropdown on click outside =====
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (openDropdown !== null) {
        const ref = dropdownRefs.current[openDropdown];
        if (ref && !ref.contains(e.target)) {
          setOpenDropdown(null);
        }
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [openDropdown]);

  // ===== Focus trap for modals =====
  const useFocusTrap = (isOpen, ref, onClose) => {
    useEffect(() => {
      if (isOpen && ref.current) {
        previousFocusRef.current = document.activeElement;

        const focusableElements = ref.current.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        setTimeout(() => firstElement?.focus(), 50);

        const handleKeyDown = (e) => {
          if (e.key === 'Escape') {
            onClose();
            return;
          }
          if (e.key !== 'Tab') return;
          if (e.shiftKey) {
            if (document.activeElement === firstElement) {
              e.preventDefault();
              lastElement.focus();
            }
          } else {
            if (document.activeElement === lastElement) {
              e.preventDefault();
              firstElement.focus();
            }
          }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => {
          document.removeEventListener('keydown', handleKeyDown);
          if (previousFocusRef.current) {
            previousFocusRef.current.focus();
          }
        };
      }
    }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps
  };

  useFocusTrap(showModal, modalRef, () => handleCloseModal());
  useFocusTrap(resetModal.isOpen, resetModalRef, () => handleCloseResetModal());

  // ===== Search & filter handlers =====
  const handleSearchChange = useCallback((e) => {
    setSearchInput(e.target.value);
    setCurrentPage(1);
  }, []);

  const handleRoleFilterChange = useCallback((e) => {
    setRoleFilter(e.target.value);
    setCurrentPage(1);
  }, []);

  // ===== Create / Edit modal =====
  const handleOpenModal = useCallback((userToEdit = null) => {
    if (userToEdit) {
      setEditingUser(userToEdit);
      setFormData({
        name: userToEdit.name || '',
        email: userToEdit.email || '',
        password: '',
        role: userToEdit.role || 'user'
      });
    } else {
      setEditingUser(null);
      setFormData({ name: '', email: '', password: '', role: 'user' });
    }
    setFormErrors({});
    setShowPassword(false);
    setShowModal(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setShowModal(false);
    setEditingUser(null);
    setFormErrors({});
  }, []);

  const validateForm = useCallback(() => {
    const errors = {};
    if (!formData.name.trim()) errors.name = 'Nome é obrigatório';
    if (!formData.email.trim()) {
      errors.email = 'Email é obrigatório';
    } else if (!isValidEmail(formData.email)) {
      errors.email = 'Formato de email inválido';
    }
    if (!editingUser) {
      if (!formData.password) {
        errors.password = 'Senha é obrigatória';
      } else if (formData.password.length < 10) {
        errors.password = 'Senha deve ter no mínimo 10 caracteres';
      }
    }
    if (!formData.role) errors.role = 'Papel é obrigatório';
    return errors;
  }, [formData, editingUser]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    setIsSubmitting(true);
    try {
      if (editingUser) {
        await updateUser(editingUser.id, {
          name: formData.name.trim(),
          email: formData.email.trim(),
          role: formData.role
        });
        setStatusMessage({
          isVisible: true,
          type: 'success',
          message: `Usuário "${formData.name}" atualizado com sucesso`
        });
      } else {
        await createUser({
          name: formData.name.trim(),
          email: formData.email.trim(),
          password: formData.password,
          role: formData.role
        });
        setStatusMessage({
          isVisible: true,
          type: 'success',
          message: `Usuário "${formData.name}" criado com sucesso`
        });
      }
      handleCloseModal();
      fetchUsers(currentPage, searchInput, roleFilter);
    } catch (err) {
      setStatusMessage({
        isVisible: true,
        type: 'error',
        message: editingUser
          ? `Erro ao atualizar usuário "${formData.name}": ${err.message || 'Tente novamente'}`
          : `Erro ao criar usuário "${formData.name}": ${err.message || 'Tente novamente'}`
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [editingUser, formData, validateForm, handleCloseModal, fetchUsers, currentPage, searchInput, roleFilter]);

  // ===== Reset password =====
  const handleOpenResetModal = useCallback((userToReset) => {
    setResetModal({ isOpen: true, user: userToReset });
    setResetPasswordValue('');
    setResetErrors({});
    setShowResetPassword(false);
    setOpenDropdown(null);
  }, []);

  const handleCloseResetModal = useCallback(() => {
    setResetModal({ isOpen: false, user: null });
    setResetPasswordValue('');
    setResetErrors({});
  }, []);

  const handleResetPasswordSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!resetPasswordValue) {
      setResetErrors({ password: 'Senha é obrigatória' });
      return;
    }
    if (resetPasswordValue.length < 10) {
      setResetErrors({ password: 'Senha deve ter no mínimo 10 caracteres' });
      return;
    }
    setIsResetting(true);
    try {
      await resetPassword(resetModal.user.id, resetPasswordValue);
      setStatusMessage({
        isVisible: true,
        type: 'success',
        message: `Senha de "${resetModal.user.name}" redefinida com sucesso`
      });
      handleCloseResetModal();
    } catch (err) {
      setStatusMessage({
        isVisible: true,
        type: 'error',
        message: `Erro ao redefinir senha: ${err.message || 'Tente novamente'}`
      });
    } finally {
      setIsResetting(false);
    }
  }, [resetPasswordValue, resetModal.user, handleCloseResetModal]);

  // ===== Deactivate =====
  const handleDeactivateClick = useCallback((userToDeactivate) => {
    setDeactivateConfirm({ isOpen: true, user: userToDeactivate });
    setOpenDropdown(null);
  }, []);

  const handleDeactivateConfirm = useCallback(async () => {
    if (!deactivateConfirm.user) return;
    const targetUser = deactivateConfirm.user;
    setDeactivateConfirm({ isOpen: false, user: null });
    try {
      await deactivateUser(targetUser.id);
      setStatusMessage({
        isVisible: true,
        type: 'success',
        message: `Usuário "${targetUser.name}" desativado com sucesso`
      });
      fetchUsers(currentPage, searchInput, roleFilter);
    } catch (err) {
      setStatusMessage({
        isVisible: true,
        type: 'error',
        message: `Erro ao desativar usuário "${targetUser.name}": ${err.message || 'Tente novamente'}`
      });
    }
  }, [deactivateConfirm.user, fetchUsers, currentPage, searchInput, roleFilter]);

  // ===== Actions dropdown =====
  const toggleDropdown = useCallback((userId) => {
    setOpenDropdown(prev => prev === userId ? null : userId);
  }, []);

  // ===== Pagination =====
  const handlePageChange = useCallback((newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  }, [totalPages]);

  const paginationRange = useMemo(() => {
    const pages = [];
    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, currentPage + 2);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  }, [currentPage, totalPages]);

  // ===== Role label & badge helpers =====
  const getRoleLabel = (role) => (role === 'admin' ? 'Admin' : 'Redator');
  const getRoleBadgeClasses = (role) =>
    role === 'admin'
      ? 'bg-blue-100 text-blue-700'
      : 'bg-gray-100 text-gray-700';
  const getStatusBadgeClasses = (isActive) =>
    isActive
      ? 'bg-green-100 text-green-700'
      : 'bg-red-100 text-red-700';

  // ===== Render =====
  return (
    <div>
      {/* Status Message */}
      {statusMessage.isVisible && (
        <div className="mb-4">
          <StatusMessage
            type={statusMessage.type}
            message={statusMessage.message}
            isVisible={statusMessage.isVisible}
            onDismiss={() => setStatusMessage({ ...statusMessage, isVisible: false })}
          />
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-dark-gray">Gerenciar Usuários</h1>
          <p className="text-medium-gray mt-1">
            Gerencie os acessos e permissões dos usuários do sistema
          </p>
        </div>
        <button
          type="button"
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 bg-tmc-orange text-white px-4 py-2.5 rounded-lg font-semibold hover:bg-tmc-orange/90 transition-colors min-h-[44px]"
          aria-label="Criar novo usuário"
        >
          <Plus size={20} aria-hidden="true" />
          Novo Usuário
        </button>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray" aria-hidden="true" />
          <input
            type="text"
            value={searchInput}
            onChange={handleSearchChange}
            placeholder="Buscar por nome ou email..."
            className="w-full pl-10 pr-4 py-2.5 border border-light-gray rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange text-sm"
            aria-label="Buscar usuários"
          />
        </div>
        <div>
          <label htmlFor="role-filter" className="sr-only">Filtrar por papel</label>
          <select
            id="role-filter"
            value={roleFilter}
            onChange={handleRoleFilterChange}
            className="w-full sm:w-auto px-4 py-2.5 border border-light-gray rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange text-sm min-h-[44px]"
          >
            <option value="">Todos</option>
            <option value="admin">Admin</option>
            <option value="user">Redator</option>
          </select>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
          <div className="bg-off-white border-b border-light-gray px-6 py-4">
            <Skeleton variant="text" className="w-1/3" />
          </div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-6 py-4 border-b border-light-gray last:border-0">
              <Skeleton variant="circle" />
              <div className="flex-1 space-y-2">
                <Skeleton variant="text" className="w-1/4" />
                <Skeleton variant="text" className="w-1/3" />
              </div>
              <Skeleton variant="button" className="w-16" />
              <Skeleton variant="button" className="w-16" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="bg-white rounded-xl border border-light-gray p-8">
          <div className="flex flex-col items-center justify-center py-8">
            <AlertCircle size={32} className="text-red-500 mb-4" />
            <p className="text-lg font-semibold text-dark-gray mb-2">Erro ao carregar usuários</p>
            <p className="text-sm text-medium-gray mb-4">{error}</p>
            <button
              onClick={handleRetry}
              className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center gap-2"
            >
              <RefreshCw size={16} />
              Tentar novamente
            </button>
          </div>
        </div>
      )}

      {/* Users Table (Desktop) */}
      {!isLoading && !error && (
        <div className="hidden md:block bg-white rounded-xl border border-light-gray">
          <table className="w-full" role="table" aria-label="Lista de usuários">
            <thead className="bg-off-white border-b border-light-gray rounded-t-xl">
              <tr>
                <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                  Nome
                </th>
                <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                  Email
                </th>
                <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                  Papel
                </th>
                <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                  Status
                </th>
                <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                  Último Login
                </th>
                <th scope="col" className="text-right px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center">
                    <UserIcon size={40} className="mx-auto text-light-gray mb-3" />
                    <p className="text-medium-gray font-medium">Nenhum usuário encontrado</p>
                    <p className="text-sm text-medium-gray mt-1">
                      {searchInput || roleFilter
                        ? 'Tente ajustar os filtros de busca'
                        : 'Clique em "Novo Usuário" para adicionar o primeiro'}
                    </p>
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="border-b border-light-gray last:border-0 hover:bg-off-white/50">
                    {/* Nome + Avatar */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 rounded-full bg-tmc-orange text-white flex items-center justify-center text-sm font-semibold flex-shrink-0"
                          aria-hidden="true"
                        >
                          {(u.name || '?').charAt(0).toUpperCase()}
                        </div>
                        <span className="font-medium text-dark-gray">{u.name}</span>
                      </div>
                    </td>

                    {/* Email */}
                    <td className="px-6 py-4 text-sm text-medium-gray">
                      {u.email}
                    </td>

                    {/* Papel */}
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${getRoleBadgeClasses(u.role)}`}>
                        {u.role === 'admin'
                          ? <Shield size={12} aria-hidden="true" />
                          : <UserIcon size={12} aria-hidden="true" />
                        }
                        {getRoleLabel(u.role)}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4">
                      <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadgeClasses(u.isActive !== false)}`}>
                        {u.isActive !== false ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>

                    {/* Último Login */}
                    <td className="px-6 py-4 text-sm text-medium-gray">
                      {formatLastLogin(u.lastLogin)}
                    </td>

                    {/* Ações */}
                    <td className="px-6 py-4">
                      <div
                        className="flex justify-end relative"
                        ref={(el) => { dropdownRefs.current[u.id] = el; }}
                      >
                        <button
                          type="button"
                          onClick={() => toggleDropdown(u.id)}
                          className="p-2 hover:bg-light-gray rounded-lg transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                          aria-label={`Ações para ${u.name}`}
                          aria-haspopup="true"
                          aria-expanded={openDropdown === u.id}
                        >
                          <MoreVertical size={18} className="text-medium-gray" aria-hidden="true" />
                        </button>

                        {openDropdown === u.id && (
                          <div className="absolute right-0 top-full mt-1 w-48 bg-white shadow-lg rounded-lg border border-light-gray py-1 z-30">
                            <button
                              type="button"
                              onClick={() => {
                                handleOpenModal(u);
                                setOpenDropdown(null);
                              }}
                              className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-dark-gray hover:bg-off-white transition-colors text-left"
                            >
                              <Edit2 size={15} aria-hidden="true" />
                              Editar
                            </button>
                            <button
                              type="button"
                              onClick={() => handleOpenResetModal(u)}
                              className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-dark-gray hover:bg-off-white transition-colors text-left"
                            >
                              <KeyRound size={15} aria-hidden="true" />
                              Resetar Senha
                            </button>
                            {currentUser?.id !== u.id && (u.isActive !== false) && (
                              <button
                                type="button"
                                onClick={() => handleDeactivateClick(u)}
                                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors text-left"
                              >
                                <UserX size={15} aria-hidden="true" />
                                Desativar
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Users Cards (Mobile) */}
      {!isLoading && !error && (
        <div className="md:hidden space-y-4">
          {users.length === 0 ? (
            <div className="bg-white rounded-xl border border-light-gray p-8 text-center">
              <UserIcon size={40} className="mx-auto text-light-gray mb-3" />
              <p className="text-medium-gray font-medium">Nenhum usuário encontrado</p>
              <p className="text-sm text-medium-gray mt-1">
                {searchInput || roleFilter
                  ? 'Tente ajustar os filtros de busca'
                  : 'Clique em "Novo Usuário" para adicionar o primeiro'}
              </p>
            </div>
          ) : (
            users.map((u) => (
              <div key={u.id} className="bg-white rounded-xl border border-light-gray p-4">
                {/* Header with avatar and actions */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-8 h-8 rounded-full bg-tmc-orange text-white flex items-center justify-center text-sm font-semibold flex-shrink-0"
                      aria-hidden="true"
                    >
                      {(u.name || '?').charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="font-medium text-dark-gray">{u.name}</h3>
                      <p className="text-xs text-medium-gray">{u.email}</p>
                    </div>
                  </div>
                  <div
                    className="relative"
                    ref={(el) => { dropdownRefs.current[`mobile-${u.id}`] = el; }}
                  >
                    <button
                      type="button"
                      onClick={() => toggleDropdown(`mobile-${u.id}`)}
                      className="p-2 hover:bg-light-gray rounded-lg transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                      aria-label={`Ações para ${u.name}`}
                      aria-haspopup="true"
                      aria-expanded={openDropdown === `mobile-${u.id}`}
                    >
                      <MoreVertical size={18} className="text-medium-gray" aria-hidden="true" />
                    </button>

                    {openDropdown === `mobile-${u.id}` && (
                      <div className="absolute right-0 top-full mt-1 w-48 bg-white shadow-lg rounded-lg border border-light-gray py-1 z-30">
                        <button
                          type="button"
                          onClick={() => {
                            handleOpenModal(u);
                            setOpenDropdown(null);
                          }}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-dark-gray hover:bg-off-white transition-colors text-left"
                        >
                          <Edit2 size={15} aria-hidden="true" />
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleOpenResetModal(u)}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-dark-gray hover:bg-off-white transition-colors text-left"
                        >
                          <KeyRound size={15} aria-hidden="true" />
                          Resetar Senha
                        </button>
                        {currentUser?.id !== u.id && (u.isActive !== false) && (
                          <button
                            type="button"
                            onClick={() => handleDeactivateClick(u)}
                            className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors text-left"
                          >
                            <UserX size={15} aria-hidden="true" />
                            Desativar
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Badges */}
                <div className="flex items-center gap-2 mb-2">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${getRoleBadgeClasses(u.role)}`}>
                    {u.role === 'admin'
                      ? <Shield size={12} aria-hidden="true" />
                      : <UserIcon size={12} aria-hidden="true" />
                    }
                    {getRoleLabel(u.role)}
                  </span>
                  <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadgeClasses(u.isActive !== false)}`}>
                    {u.isActive !== false ? 'Ativo' : 'Inativo'}
                  </span>
                </div>

                {/* Last login */}
                <p className="text-xs text-medium-gray">
                  Último login: {formatLastLogin(u.lastLogin)}
                </p>
              </div>
            ))
          )}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && !error && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            type="button"
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-3 py-2 text-sm border border-light-gray rounded-lg hover:bg-off-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors min-h-[44px]"
            aria-label="Página anterior"
          >
            Anterior
          </button>

          {paginationRange.map((page) => (
            <button
              key={page}
              type="button"
              onClick={() => handlePageChange(page)}
              className={`px-3 py-2 text-sm rounded-lg transition-colors min-h-[44px] min-w-[44px] ${
                page === currentPage
                  ? 'bg-tmc-orange text-white font-semibold'
                  : 'border border-light-gray hover:bg-off-white text-dark-gray'
              }`}
              aria-label={`Página ${page}`}
              aria-current={page === currentPage ? 'page' : undefined}
            >
              {page}
            </button>
          ))}

          <button
            type="button"
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-3 py-2 text-sm border border-light-gray rounded-lg hover:bg-off-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors min-h-[44px]"
            aria-label="Próxima página"
          >
            Próximo
          </button>
        </div>
      )}

      {/* Stats Footer */}
      {!isLoading && !error && users.length > 0 && (
        <div className="mt-4 text-center text-sm text-medium-gray" role="status" aria-live="polite">
          Mostrando <span className="font-semibold text-dark-gray">{users.length}</span> de{' '}
          <span className="font-semibold text-dark-gray">{totalUsers}</span> usuários
        </div>
      )}

      {/* Create / Edit Modal */}
      {showModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="user-modal-title"
        >
          <div ref={modalRef} className="bg-white rounded-xl w-full max-w-md p-6 m-4 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 id="user-modal-title" className="text-xl font-bold text-dark-gray">
                {editingUser ? 'Editar Usuário' : 'Novo Usuário'}
              </h2>
              <button
                type="button"
                onClick={handleCloseModal}
                className="p-2 hover:bg-off-white rounded-lg transition-colors min-h-[44px] min-w-[44px]"
                aria-label="Fechar modal"
              >
                <X size={20} className="text-medium-gray" aria-hidden="true" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {/* Nome */}
              <div>
                <label htmlFor="user-name" className="block text-sm font-medium text-dark-gray mb-1">
                  Nome <span className="text-red-500" aria-label="obrigatório">*</span>
                </label>
                <div className="relative">
                  <UserIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray" aria-hidden="true" />
                  <input
                    id="user-name"
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => {
                      setFormData({ ...formData, name: e.target.value });
                      if (formErrors.name) setFormErrors({ ...formErrors, name: '' });
                    }}
                    className={`w-full pl-10 pr-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange ${
                      formErrors.name ? 'border-red-400' : 'border-light-gray'
                    }`}
                    placeholder="Nome completo"
                    aria-required="true"
                    aria-invalid={!!formErrors.name}
                    aria-describedby={formErrors.name ? 'user-name-error' : undefined}
                  />
                </div>
                {formErrors.name && (
                  <p id="user-name-error" className="text-xs text-red-500 mt-1">{formErrors.name}</p>
                )}
              </div>

              {/* Email */}
              <div>
                <label htmlFor="user-email" className="block text-sm font-medium text-dark-gray mb-1">
                  Email <span className="text-red-500" aria-label="obrigatório">*</span>
                </label>
                <div className="relative">
                  <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray" aria-hidden="true" />
                  <input
                    id="user-email"
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => {
                      setFormData({ ...formData, email: e.target.value });
                      if (formErrors.email) setFormErrors({ ...formErrors, email: '' });
                    }}
                    className={`w-full pl-10 pr-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange ${
                      formErrors.email ? 'border-red-400' : 'border-light-gray'
                    }`}
                    placeholder="usuario@email.com"
                    aria-required="true"
                    aria-invalid={!!formErrors.email}
                    aria-describedby={formErrors.email ? 'user-email-error' : undefined}
                  />
                </div>
                {formErrors.email && (
                  <p id="user-email-error" className="text-xs text-red-500 mt-1">{formErrors.email}</p>
                )}
              </div>

              {/* Senha (only for create) */}
              {!editingUser && (
                <div>
                  <label htmlFor="user-password" className="block text-sm font-medium text-dark-gray mb-1">
                    Senha <span className="text-red-500" aria-label="obrigatório">*</span>
                  </label>
                  <div className="relative">
                    <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray" aria-hidden="true" />
                    <input
                      id="user-password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={formData.password}
                      onChange={(e) => {
                        setFormData({ ...formData, password: e.target.value });
                        if (formErrors.password) setFormErrors({ ...formErrors, password: '' });
                      }}
                      className={`w-full pl-10 pr-12 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange ${
                        formErrors.password ? 'border-red-400' : 'border-light-gray'
                      }`}
                      placeholder="Mínimo 10 caracteres"
                      minLength={10}
                      aria-required="true"
                      aria-invalid={!!formErrors.password}
                      aria-describedby={formErrors.password ? 'user-password-error' : 'user-password-help'}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-medium-gray hover:text-dark-gray transition-colors"
                      aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                    >
                      {showPassword ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
                    </button>
                  </div>
                  {formErrors.password ? (
                    <p id="user-password-error" className="text-xs text-red-500 mt-1">{formErrors.password}</p>
                  ) : (
                    <p id="user-password-help" className="text-xs text-medium-gray mt-1">Mínimo de 10 caracteres</p>
                  )}
                </div>
              )}

              {/* Papel */}
              <div>
                <label htmlFor="user-role" className="block text-sm font-medium text-dark-gray mb-1">
                  Papel <span className="text-red-500" aria-label="obrigatório">*</span>
                </label>
                <div className="relative">
                  <Shield size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray" aria-hidden="true" />
                  <select
                    id="user-role"
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full pl-10 pr-4 py-2.5 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange appearance-none bg-white"
                    aria-required="true"
                  >
                    <option value="user">Redator</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="flex-1 py-2.5 border border-light-gray rounded-lg text-medium-gray hover:bg-off-white transition-colors min-h-[44px]"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-2.5 bg-tmc-orange text-white rounded-lg font-semibold hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px] flex items-center justify-center gap-2"
                >
                  {isSubmitting && <Spinner size="sm" className="border-white border-t-transparent" />}
                  {isSubmitting ? 'Salvando...' : (editingUser ? 'Salvar alterações' : 'Criar usuário')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {resetModal.isOpen && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="reset-modal-title"
        >
          <div ref={resetModalRef} className="bg-white rounded-xl w-full max-w-md p-6 m-4 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 id="reset-modal-title" className="text-xl font-bold text-dark-gray">
                Resetar Senha
              </h2>
              <button
                type="button"
                onClick={handleCloseResetModal}
                className="p-2 hover:bg-off-white rounded-lg transition-colors min-h-[44px] min-w-[44px]"
                aria-label="Fechar modal"
              >
                <X size={20} className="text-medium-gray" aria-hidden="true" />
              </button>
            </div>

            <p className="text-sm text-medium-gray mb-4">
              Definir nova senha para <span className="font-semibold text-dark-gray">{resetModal.user?.name}</span>
            </p>

            <form onSubmit={handleResetPasswordSubmit} className="space-y-4" noValidate>
              <div>
                <label htmlFor="reset-password" className="block text-sm font-medium text-dark-gray mb-1">
                  Nova Senha <span className="text-red-500" aria-label="obrigatório">*</span>
                </label>
                <div className="relative">
                  <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray" aria-hidden="true" />
                  <input
                    id="reset-password"
                    type={showResetPassword ? 'text' : 'password'}
                    required
                    value={resetPasswordValue}
                    onChange={(e) => {
                      setResetPasswordValue(e.target.value);
                      if (resetErrors.password) setResetErrors({});
                    }}
                    className={`w-full pl-10 pr-12 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange ${
                      resetErrors.password ? 'border-red-400' : 'border-light-gray'
                    }`}
                    placeholder="Mínimo 10 caracteres"
                    minLength={10}
                    aria-required="true"
                    aria-invalid={!!resetErrors.password}
                    aria-describedby={resetErrors.password ? 'reset-password-error' : 'reset-password-help'}
                  />
                  <button
                    type="button"
                    onClick={() => setShowResetPassword(!showResetPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-medium-gray hover:text-dark-gray transition-colors"
                    aria-label={showResetPassword ? 'Ocultar senha' : 'Mostrar senha'}
                  >
                    {showResetPassword ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
                  </button>
                </div>
                {resetErrors.password ? (
                  <p id="reset-password-error" className="text-xs text-red-500 mt-1">{resetErrors.password}</p>
                ) : (
                  <p id="reset-password-help" className="text-xs text-medium-gray mt-1">Mínimo de 10 caracteres</p>
                )}
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleCloseResetModal}
                  className="flex-1 py-2.5 border border-light-gray rounded-lg text-medium-gray hover:bg-off-white transition-colors min-h-[44px]"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isResetting}
                  className="flex-1 py-2.5 bg-tmc-orange text-white rounded-lg font-semibold hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px] flex items-center justify-center gap-2"
                >
                  {isResetting && <Spinner size="sm" className="border-white border-t-transparent" />}
                  {isResetting ? 'Redefinindo...' : 'Redefinir Senha'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Deactivate Confirmation Dialog */}
      <ConfirmDialog
        isOpen={deactivateConfirm.isOpen}
        onClose={() => setDeactivateConfirm({ isOpen: false, user: null })}
        onConfirm={handleDeactivateConfirm}
        title="Desativar Usuário"
        message={`Tem certeza que deseja desativar o usuário "${deactivateConfirm.user?.name}"? O usuário perderá o acesso ao sistema imediatamente.`}
        confirmText="Desativar"
        cancelText="Cancelar"
        variant="danger"
      />
    </div>
  );
};

export default UsuariosPage;
