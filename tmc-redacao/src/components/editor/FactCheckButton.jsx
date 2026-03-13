import { ShieldCheck, Loader2, Eye, EyeOff } from 'lucide-react';
import PropTypes from 'prop-types';
import Tooltip from '../ui/Tooltip';

const ASI_THRESHOLDS = {
  HIGH: 80,
  MEDIUM: 50,
};

function getAsiBadgeClasses(safetyIndex) {
  if (safetyIndex >= ASI_THRESHOLDS.HIGH) {
    return 'bg-green-100 text-green-700 hover:bg-green-200';
  }
  if (safetyIndex >= ASI_THRESHOLDS.MEDIUM) {
    return 'bg-amber-100 text-amber-700 hover:bg-amber-200';
  }
  return 'bg-red-100 text-red-700 hover:bg-red-200';
}

export default function FactCheckButton({
  isScanning = false,
  scanResult = null,
  highlightsVisible = false,
  contentLength = 0,
  contentChanged = false,
  onScan,
  onOpenModal,
  onToggleHighlights,
  disabled = false,
}) {
  const isButtonDisabled = isScanning || disabled || contentLength < 100;

  return (
    <div className="flex items-center gap-2">
      {/* Element 1: Scan Button */}
      <button
        type="button"
        onClick={onScan}
        disabled={isButtonDisabled}
        className={`flex items-center gap-2 px-3 py-1.5 bg-off-white text-dark-gray hover:bg-light-gray rounded-lg text-sm font-medium transition-colors flex-shrink-0 ${
          isButtonDisabled ? 'opacity-70 cursor-wait' : ''
        }`}
      >
        {isScanning ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            <span className="hidden md:inline">Verificando...</span>
          </>
        ) : (
          <>
            <ShieldCheck size={16} />
            <span className="hidden md:inline">Verificar Segurança</span>
          </>
        )}
      </button>

      {/* Element 2: ASI Badge */}
      {scanResult && (
        <Tooltip content={scanResult.safety_label} position="bottom">
          <button
            type="button"
            onClick={onOpenModal}
            className={`relative inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold cursor-pointer transition-all ${getAsiBadgeClasses(scanResult.safety_index)}`}
          >
            ASI {scanResult.safety_index}
            {contentChanged && (
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            )}
          </button>
        </Tooltip>
      )}

      {/* Element 3: Highlights Toggle */}
      {scanResult && scanResult.claims?.length > 0 && (
        <button
          type="button"
          onClick={onToggleHighlights}
          aria-pressed={highlightsVisible}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
            highlightsVisible
              ? 'bg-tmc-orange/10 text-tmc-orange border border-tmc-orange/30'
              : 'bg-off-white text-medium-gray border border-light-gray'
          }`}
        >
          {highlightsVisible ? <Eye size={16} /> : <EyeOff size={16} />}
          <span className="hidden md:inline">Destaques</span>
        </button>
      )}
    </div>
  );
}

FactCheckButton.propTypes = {
  isScanning: PropTypes.bool,
  scanResult: PropTypes.object,
  highlightsVisible: PropTypes.bool,
  contentLength: PropTypes.number,
  contentChanged: PropTypes.bool,
  onScan: PropTypes.func.isRequired,
  onOpenModal: PropTypes.func,
  onToggleHighlights: PropTypes.func,
  disabled: PropTypes.bool,
};
