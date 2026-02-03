import { useState, useCallback, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Clipboard, Trash2, FileText } from 'lucide-react';
import {
  SourceBadge,
  ContentStats
} from '../../../components/criar';

/**
 * TextoBaseZero - Variante da pagina Texto-Base para Criar do Zero
 *
 * Permite:
 * - Colar qualquer texto livre como ponto de partida
 * - Editar o texto diretamente
 * - Ver estatisticas de palavras
 */

const TextoBaseZero = ({
  fonte,
  onChangeSource,
  onDataChange
}) => {
  // State para o texto colado
  const [textoBase, setTextoBase] = useState(fonte?.dados?.texto || '');

  // Estatisticas
  const stats = useMemo(() => {
    const words = textoBase.trim() ? textoBase.split(/\s+/).filter(Boolean).length : 0;
    const chars = textoBase.length;
    const paragraphs = textoBase.trim() ? textoBase.split(/\n\n+/).filter(p => p.trim()).length : 0;

    return {
      words,
      chars,
      paragraphs
    };
  }, [textoBase]);

  // Handler para colar do clipboard
  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setTextoBase(prev => prev ? `${prev}\n\n${text}` : text);
      }
    } catch (err) {
      console.error('Erro ao colar:', err);
      // Fallback: foca no textarea para paste manual
    }
  }, []);

  // Handler para limpar
  const handleClear = useCallback(() => {
    setTextoBase('');
  }, []);

  // Handler para mudanca de texto
  const handleTextChange = useCallback((e) => {
    setTextoBase(e.target.value);
  }, []);

  // Notificar mudancas para o pai
  useEffect(() => {
    if (onDataChange) {
      onDataChange({
        selectedTopics: textoBase.trim() ? ['texto-livre'] : [],
        topicTexts: { 'texto-livre': textoBase },
        wordCount: stats.words
      });
    }
  }, [textoBase, stats.words, onDataChange]);

  return (
    <div className="space-y-6">
      <SourceBadge
        type="zero"
        title="Texto Livre"
        subtitle={stats.words > 0 ? `${stats.words} palavras` : 'Cole seu texto'}
        onChangeSource={onChangeSource}
      />

      {/* Area principal */}
      <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
        {/* Header com acoes */}
        <div className="p-4 border-b border-light-gray flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText size={20} className="text-tmc-orange" />
            <h3 className="font-semibold text-dark-gray">Texto-Base</h3>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePaste}
              className="flex items-center gap-2 px-3 py-1.5 text-sm border border-light-gray rounded-lg text-medium-gray hover:text-tmc-orange hover:border-tmc-orange transition-colors"
            >
              <Clipboard size={16} />
              Colar
            </button>
            <button
              onClick={handleClear}
              disabled={!textoBase}
              className="flex items-center gap-2 px-3 py-1.5 text-sm border border-light-gray rounded-lg text-medium-gray hover:text-red-500 hover:border-red-300 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Trash2 size={16} />
              Limpar
            </button>
          </div>
        </div>

        {/* Textarea */}
        <div className="p-4">
          <textarea
            value={textoBase}
            onChange={handleTextChange}
            placeholder="Cole aqui o texto que servirá como base para sua matéria...

Pode ser:
• Um artigo de outro site
• Uma nota de imprensa
• Um comunicado oficial
• Qualquer texto que você queira transformar em matéria

Dica: Quanto mais detalhado o texto-base, melhor será o resultado da geração com IA."
            className="w-full h-96 p-4 border border-light-gray rounded-lg resize-none text-sm text-dark-gray leading-relaxed focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange placeholder:text-medium-gray/60"
          />

          {/* Info */}
          {textoBase && (
            <div className="mt-3 flex items-center gap-4 text-xs text-medium-gray">
              <span>{stats.words} palavras</span>
              <span>{stats.chars} caracteres</span>
              <span>{stats.paragraphs} parágrafo{stats.paragraphs !== 1 ? 's' : ''}</span>
            </div>
          )}
        </div>

        {/* Footer com stats */}
        <ContentStats
          selectedCount={textoBase.trim() ? 1 : 0}
          totalCount={1}
          wordCount={stats.words}
          variant="zero"
        />
      </div>

      {/* Dica */}
      {!textoBase && (
        <div className="bg-orange-50 border border-orange-100 rounded-lg p-4">
          <p className="text-sm text-dark-gray">
            <strong>Dica:</strong> Você pode colar qualquer texto aqui - artigos,
            comunicados, notas de imprensa, ou até mesmo rascunhos.
            A IA usará esse conteúdo como base para gerar sua matéria.
          </p>
        </div>
      )}
    </div>
  );
};

TextoBaseZero.propTypes = {
  fonte: PropTypes.shape({
    tipo: PropTypes.string,
    dados: PropTypes.shape({
      texto: PropTypes.string
    })
  }),
  onChangeSource: PropTypes.func,
  onDataChange: PropTypes.func
};

export default TextoBaseZero;
