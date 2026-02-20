import { ShieldX } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

function AccessDenied() {
  const navigate = useNavigate();
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center max-w-md px-4">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <ShieldX className="w-8 h-8 text-red-500" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold text-dark-gray mb-3">Acesso Restrito</h1>
        <p className="text-medium-gray mb-8">
          Você não tem permissão para acessar esta página. Entre em contato com o administrador.
        </p>
        <button
          onClick={() => navigate('/')}
          className="bg-tmc-orange hover:bg-tmc-orange/90 text-white font-medium px-6 py-3 rounded-lg transition-colors"
        >
          Voltar para a Redação
        </button>
      </div>
    </div>
  );
}

export default AccessDenied;
