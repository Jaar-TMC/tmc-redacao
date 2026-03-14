import { useState } from 'react';
import { Power, Activity, DollarSign, Clock, AlertTriangle, X } from 'lucide-react';
import { useAiStatus } from '../context/AiStatusContext';

const SistemaPage = () => {
  const {
    aiPaused, pausedBy, pausedAt, estimatedSavings,
    hoursPaused, avgHourlyCost, toggleAi, loading,
  } = useAiStatus();
  const [showConfirm, setShowConfirm] = useState(false);

  const handleToggle = async () => {
    if (!aiPaused) {
      // Show confirmation before pausing
      setShowConfirm(true);
      return;
    }
    // Resume directly
    await toggleAi(false);
  };

  const confirmPause = async () => {
    setShowConfirm(false);
    await toggleAi(true);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Intl.DateTimeFormat('pt-BR', {
        dateStyle: 'short',
        timeStyle: 'short',
      }).format(new Date(dateStr));
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sistema</h1>
        <p className="text-sm text-gray-500 mt-1">Controle geral das operações de IA</p>
      </div>

      {/* Main Kill Switch Card */}
      <div className={`rounded-xl border-2 p-6 transition-colors ${
        aiPaused
          ? 'border-red-300 bg-red-50'
          : 'border-emerald-300 bg-emerald-50'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              aiPaused ? 'bg-red-100' : 'bg-emerald-100'
            }`}>
              <Power size={24} className={aiPaused ? 'text-red-600' : 'text-emerald-600'} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {aiPaused ? 'IA Pausada' : 'IA Ativa'}
              </h2>
              <p className="text-sm text-gray-600">
                {aiPaused
                  ? 'Todas as operações estão pausadas, incluindo coleta RSS.'
                  : 'Geração, classificação, scoring e coleta RSS estão operacionais.'}
              </p>
            </div>
          </div>

          {/* Toggle Switch */}
          <button
            type="button"
            onClick={handleToggle}
            disabled={loading}
            className={`relative inline-flex h-8 w-14 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 ${
              aiPaused
                ? 'bg-red-500 focus:ring-red-500'
                : 'bg-emerald-500 focus:ring-emerald-500'
            } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            role="switch"
            aria-checked={!aiPaused}
            aria-label={aiPaused ? 'Reativar IA' : 'Pausar IA'}
          >
            <span className={`pointer-events-none inline-block h-7 w-7 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
              aiPaused ? 'translate-x-0' : 'translate-x-6'
            }`} />
          </button>
        </div>
      </div>

      {/* Status Info Cards - only when paused */}
      {aiPaused && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Time paused */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock size={16} className="text-gray-400" />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Pausado há</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {hoursPaused < 1
                ? `${Math.round(hoursPaused * 60)} min`
                : `${hoursPaused.toFixed(1)}h`}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Por {pausedBy || 'admin'} em {formatDate(pausedAt)}
            </p>
          </div>

          {/* Estimated savings */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign size={16} className="text-gray-400" />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Economia estimada</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">
              ${estimatedSavings.toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Custo médio: ${avgHourlyCost.toFixed(2)}/hora
            </p>
          </div>

          {/* Impact */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity size={16} className="text-gray-400" />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Impacto</span>
            </div>
            <div className="space-y-1.5 mt-1">
              <div className="flex items-center gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                <span className="text-gray-700">Geração de artigos</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                <span className="text-gray-700">Classificação, scoring, embeddings</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                <span className="text-gray-700">Coleta RSS</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                <AlertTriangle size={20} className="text-amber-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Pausar todas as operações de IA?</h3>
              <button
                onClick={() => setShowConfirm(false)}
                className="ml-auto p-1 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Fechar"
              >
                <X size={18} className="text-gray-400" />
              </button>
            </div>

            <div className="space-y-3 mb-6">
              <p className="text-sm text-gray-600">As seguintes operações serão pausadas:</p>
              <ul className="text-sm text-gray-700 space-y-1.5 pl-4">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  Geração de artigos
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  Classificação e scoring
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  Embeddings e clustering
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  Fact-check e verificação
                </li>
              </ul>
              <p className="text-sm text-amber-700 bg-amber-50 rounded-lg p-3">
                Todas as operações serão interrompidas, incluindo a coleta de RSS.
              </p>
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={confirmPause}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50"
              >
                {loading ? 'Pausando...' : 'Pausar IA'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SistemaPage;
