import Spinner from '../ui/Spinner';
import LogoTMC from '../../assets/logo-tmc.svg?react';

function AuthLoadingScreen() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-off-white" role="status" aria-label="Verificando autenticação">
      <LogoTMC className="h-12 w-auto mb-6 opacity-60" aria-hidden="true" />
      <Spinner size="lg" />
      <p className="mt-4 text-sm text-medium-gray">Verificando autenticação...</p>
    </div>
  );
}

export default AuthLoadingScreen;
