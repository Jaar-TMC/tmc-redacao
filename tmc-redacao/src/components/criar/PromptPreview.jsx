import { useState, useMemo, useCallback } from 'react';
import PropTypes from 'prop-types';
import {
  ChevronDown, ChevronRight, Copy, Check, Code,
  FileText, Hash, Cpu
} from 'lucide-react';
import { getFullPromptPreview } from '../../utils/promptBuilder';

/**
 * PromptPreview Component
 *
 * Displays a live preview of the AI prompts that will be sent to Claude.
 * Shows system prompt (collapsible) and user prompt with stats.
 */
const PromptPreview = ({ config, textoBase }) => {
  const [systemExpanded, setSystemExpanded] = useState(false);
  const [copiedSystem, setCopiedSystem] = useState(false);
  const [copiedUser, setCopiedUser] = useState(false);

  // Generate prompts based on current config
  const { systemPrompt, userPrompt, stats } = useMemo(() => {
    return getFullPromptPreview(config, textoBase);
  }, [config, textoBase]);

  // Copy to clipboard handlers
  const copyToClipboard = useCallback(async (text, type) => {
    try {
      await navigator.clipboard.writeText(text);
      if (type === 'system') {
        setCopiedSystem(true);
        setTimeout(() => setCopiedSystem(false), 2000);
      } else {
        setCopiedUser(true);
        setTimeout(() => setCopiedUser(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-800 px-4 py-3 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code size={18} className="text-tmc-orange" />
            <h3 className="text-sm font-semibold text-white">
              Prompt Preview
            </h3>
            <span className="text-xs text-gray-400 bg-gray-700 px-2 py-0.5 rounded">
              Modo Avancado
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <div className="flex items-center gap-1">
              <Hash size={12} />
              <span>{stats.totalChars.toLocaleString()} chars</span>
            </div>
            <div className="flex items-center gap-1">
              <Cpu size={12} />
              <span>~{stats.estimatedTokens.toLocaleString()} tokens</span>
            </div>
          </div>
        </div>
      </div>

      {/* System Prompt - Collapsible */}
      <div className="border-b border-gray-700">
        <button
          onClick={() => setSystemExpanded(!systemExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            {systemExpanded ? (
              <ChevronDown size={16} className="text-gray-400" />
            ) : (
              <ChevronRight size={16} className="text-gray-400" />
            )}
            <span className="text-sm font-medium text-gray-300">
              System Prompt
            </span>
            <span className="text-xs text-gray-500">
              ({stats.systemChars.toLocaleString()} chars)
            </span>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              copyToClipboard(systemPrompt, 'system');
            }}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors px-2 py-1 rounded hover:bg-gray-700"
          >
            {copiedSystem ? (
              <>
                <Check size={12} className="text-green-400" />
                <span className="text-green-400">Copiado!</span>
              </>
            ) : (
              <>
                <Copy size={12} />
                <span>Copiar</span>
              </>
            )}
          </button>
        </button>

        {systemExpanded && (
          <div className="px-4 pb-4">
            <pre className="bg-gray-950 rounded-lg p-4 text-xs text-gray-300 font-mono whitespace-pre-wrap overflow-x-auto max-h-80 overflow-y-auto">
              {systemPrompt}
            </pre>
          </div>
        )}
      </div>

      {/* User Prompt - Always Visible */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText size={16} className="text-tmc-orange" />
            <span className="text-sm font-medium text-gray-300">
              User Prompt
            </span>
            <span className="text-xs text-gray-500">
              ({stats.userChars.toLocaleString()} chars)
            </span>
          </div>
          <button
            onClick={() => copyToClipboard(userPrompt, 'user')}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors px-2 py-1 rounded hover:bg-gray-700"
          >
            {copiedUser ? (
              <>
                <Check size={12} className="text-green-400" />
                <span className="text-green-400">Copiado!</span>
              </>
            ) : (
              <>
                <Copy size={12} />
                <span>Copiar</span>
              </>
            )}
          </button>
        </div>

        <pre className="bg-gray-950 rounded-lg p-4 text-xs text-gray-300 font-mono whitespace-pre-wrap overflow-x-auto max-h-96 overflow-y-auto">
          {userPrompt}
        </pre>
      </div>

      {/* Footer with tips */}
      <div className="bg-gray-800/50 px-4 py-2 border-t border-gray-700">
        <p className="text-xs text-gray-500">
          Este preview mostra exatamente o prompt que sera enviado para o Claude.
          Altere as configuracoes acima para ver as mudancas em tempo real.
        </p>
      </div>
    </div>
  );
};

PromptPreview.propTypes = {
  config: PropTypes.shape({
    categoria: PropTypes.string,
    tom: PropTypes.string,
    tipoMateria: PropTypes.string,
    modoOpinativo: PropTypes.bool,
    orientacaoLide: PropTypes.string,
    citacoes: PropTypes.array,
    contexto: PropTypes.string,
    creditos: PropTypes.string,
    instrucoes: PropTypes.string,
  }).isRequired,
  textoBase: PropTypes.string.isRequired,
};

export default PromptPreview;
