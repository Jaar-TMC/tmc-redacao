import PropTypes from 'prop-types';
import { Sparkles } from 'lucide-react';

/**
 * Step Two component - Loading/processing step
 * @param {Object} props
 * @param {number} props.loadingProgress - Progress percentage (0-100)
 * @param {string} props.loadingText - Current loading status text
 */
const StepTwo = ({ loadingProgress, loadingText }) => {
  return (
    <div className="min-h-screen pt-16 bg-off-white">
      {/* Header */}
      <div className="bg-white border-b border-light-gray sticky top-16 z-40">
        <div className="flex items-center justify-between px-4 md:px-6 py-3">
          <div className="flex items-center gap-2 md:gap-4">
            <div>
              <p className="text-xs text-medium-gray hidden sm:block">Redação &gt; Criar com Inspiração</p>
              <h1 className="text-base md:text-lg font-bold text-dark-gray">Configure a Geração (Passo 2 de 3)</h1>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-medium-gray">
            <span className="w-6 h-6 bg-tmc-orange text-white rounded-full flex items-center justify-center text-xs font-bold">
              2
            </span>
            <span className="hidden sm:inline">de 3</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center" style={{ height: 'calc(100vh - 8rem)' }}>
        <div className="text-center">
          <div className="w-24 h-24 mx-auto mb-6 relative">
            <div className="absolute inset-0 border-4 border-light-gray rounded-full"></div>
            <div
              className="absolute inset-0 border-4 border-tmc-orange rounded-full animate-spin"
              style={{
                clipPath: 'polygon(0 0, 100% 0, 100% 100%, 0 100%)',
                transform: `rotate(${loadingProgress * 3.6}deg)`
              }}
            ></div>
            <div className="absolute inset-2 bg-white rounded-full flex items-center justify-center">
              <Sparkles size={32} className="text-tmc-orange" />
            </div>
          </div>

          <p className="text-lg font-semibold text-dark-gray mb-2">{loadingText}</p>

          <div className="w-64 h-2 bg-off-white rounded-full overflow-hidden mx-auto mb-4">
            <div
              className="h-full bg-tmc-orange rounded-full transition-all duration-300"
              style={{ width: `${loadingProgress}%` }}
            ></div>
          </div>

          <p className="text-sm text-medium-gray">Aguarde enquanto geramos seu conteúdo...</p>
        </div>
      </div>
    </div>
  );
};

StepTwo.propTypes = {
  loadingProgress: PropTypes.number.isRequired,
  loadingText: PropTypes.string.isRequired
};

export default StepTwo;
