import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useDocumentTitle } from '../../hooks';
import AuthLayout from '../../components/auth/AuthLayout';
import LoginForm from '../../components/auth/LoginForm';

function LoginPage() {
  useDocumentTitle('Login - TMC Redação');
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Already authenticated -> redirect
  if (authLoading) return null; // Wait for auth check
  if (isAuthenticated) return <Navigate to="/" replace />;

  const handleLogin = async (email, password, rememberMe) => {
    setIsSubmitting(true);
    setError(null);
    try {
      await login(email, password, rememberMe);
      // Navigation handled by isAuthenticated becoming true
    } catch (err) {
      // Map backend error messages
      const msg = err?.data?.error || err?.message || 'Erro ao fazer login. Tente novamente.';
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout>
      <LoginForm onSubmit={handleLogin} error={error} isLoading={isSubmitting} />
    </AuthLayout>
  );
}

export default LoginPage;
