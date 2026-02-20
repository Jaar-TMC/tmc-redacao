import { useState } from 'react';
import PropTypes from 'prop-types';
import { Eye, EyeOff } from 'lucide-react';
import Spinner from '../ui/Spinner';

function LoginForm({ onSubmit, error, isLoading }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  const validate = () => {
    const errors = {};
    if (!email.trim()) errors.email = 'Email é obrigatório';
    else if (!/\S+@\S+\.\S+/.test(email)) errors.email = 'Email inválido';
    if (!password) errors.password = 'Senha é obrigatória';
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      onSubmit(email.trim().toLowerCase(), password, rememberMe);
    }
  };

  // Determine banner color: yellow for lockout/rate limit, red for auth errors
  const isWarning = error && (error.includes('bloqueada') || error.includes('tentativas'));

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h2 className="text-2xl font-bold text-dark-gray mb-2">Bem-vindo de volta!</h2>
      <p className="text-medium-gray mb-8">Entre para continuar</p>

      {/* Error/Warning Banner */}
      {error && (
        <div
          className={`mb-6 p-4 rounded-lg text-sm ${isWarning ? 'bg-yellow-50 text-yellow-800 border border-yellow-200' : 'bg-red-50 text-red-700 border border-red-200'}`}
          role="alert"
          aria-live="polite"
        >
          {error}
        </div>
      )}

      {/* Email */}
      <div className="mb-4">
        <label htmlFor="login-email" className="block text-sm font-medium text-dark-gray mb-1">Email *</label>
        <input
          id="login-email"
          type="email"
          value={email}
          onChange={(e) => { setEmail(e.target.value); setFieldErrors(p => ({...p, email: undefined})); }}
          className={`w-full px-4 py-3 min-h-[44px] border rounded-lg focus:ring-2 focus:outline-none transition-colors ${fieldErrors.email ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-tmc-orange focus:border-tmc-orange'}`}
          placeholder="seu@email.com"
          autoComplete="email"
          aria-invalid={!!fieldErrors.email}
          aria-describedby={fieldErrors.email ? 'email-error' : undefined}
          disabled={isLoading}
        />
        {fieldErrors.email && <p id="email-error" className="mt-1 text-sm text-red-600">{fieldErrors.email}</p>}
      </div>

      {/* Password */}
      <div className="mb-4">
        <label htmlFor="login-password" className="block text-sm font-medium text-dark-gray mb-1">Senha *</label>
        <div className="relative">
          <input
            id="login-password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => { setPassword(e.target.value); setFieldErrors(p => ({...p, password: undefined})); }}
            className={`w-full px-4 py-3 pr-12 min-h-[44px] border rounded-lg focus:ring-2 focus:outline-none transition-colors ${fieldErrors.password ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-tmc-orange focus:border-tmc-orange'}`}
            placeholder="••••••••••"
            autoComplete="current-password"
            aria-invalid={!!fieldErrors.password}
            aria-describedby={fieldErrors.password ? 'password-error' : undefined}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-1"
            aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
            tabIndex={-1}
          >
            {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
          </button>
        </div>
        {fieldErrors.password && <p id="password-error" className="mt-1 text-sm text-red-600">{fieldErrors.password}</p>}
      </div>

      {/* Remember Me */}
      <div className="mb-6 flex items-center gap-2">
        <input
          id="remember-me"
          type="checkbox"
          checked={rememberMe}
          onChange={(e) => setRememberMe(e.target.checked)}
          className="w-4 h-4 rounded border-gray-300 text-tmc-orange focus:ring-tmc-orange"
          disabled={isLoading}
        />
        <label htmlFor="remember-me" className="text-sm text-medium-gray">Lembrar de mim</label>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-tmc-orange hover:bg-tmc-orange/90 disabled:opacity-60 text-white font-semibold py-3 min-h-[44px] rounded-lg transition-colors flex items-center justify-center gap-2"
        aria-busy={isLoading}
      >
        {isLoading ? <><Spinner size="sm" /> Entrando...</> : 'ENTRAR'}
      </button>

      {/* Disclaimer */}
      <p className="mt-6 text-xs text-center text-medium-gray leading-relaxed">
        Ferramenta em homologação e em melhorias constantes.
        <br />
        Em caso de problemas, entre em contato com o administrador.
      </p>
    </form>
  );
}

LoginForm.propTypes = {
  onSubmit: PropTypes.func.isRequired,
  error: PropTypes.string,
  isLoading: PropTypes.bool,
};

export default LoginForm;
