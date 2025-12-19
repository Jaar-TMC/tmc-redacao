import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';

/**
 * CriarContext
 *
 * Context para gerenciar o estado do fluxo de criação de matérias.
 * Compartilha dados entre as etapas: Fonte, Texto-Base, Configurar, Revisar e Editor.
 */

const CriarContext = createContext(undefined);

// Hook para usar o contexto
export const useCriar = () => {
  const context = useContext(CriarContext);
  if (!context) {
    throw new Error('useCriar must be used within CriarProvider');
  }
  return context;
};

// Estado inicial
const initialState = {
  // Etapa 1: Fonte selecionada
  fonte: {
    tipo: null, // 'tema' | 'feed' | 'transcription' | 'link'
    dados: null, // Dados específicos da fonte (tema, artigos do feed, trechos transcrição, etc.)
  },

  // Etapa 2: Texto-base
  textoBase: {
    blocos: [], // Array de blocos de conteúdo
    textoCompleto: '', // Texto editável completo
    modoEdicao: 'blocos', // 'blocos' | 'texto'
    blocosSelecionados: new Set(),
  },

  // Etapa 3: Configurações
  configuracoes: {
    data: new Date().toISOString().split('T')[0],
    orientacaoLide: '',
    citacoes: [],
    contexto: '',
    creditos: '',
    persona: 'imparcial', // 'imparcial' | 'analista' | 'especialista' | 'popular'
    tom: 'formal', // 'formal' | 'informal' | 'tecnico' | 'casual'
    instrucoes: '',
  },

  // Materiais complementares
  materiaisComplementares: {
    links: [],
    videos: [],
    pdfs: [],
  },

  // Etapa 4: Resultado gerado
  resultado: {
    titulo: '',
    conteudo: '',
    geradoEm: null,
  },

  // Controle de navegação
  etapaAtual: 0,
  etapasCompletas: new Set(),
};

export const CriarProvider = ({ children }) => {
  const [state, setState] = useState(initialState);

  // === Ações para Fonte (Etapa 1) ===
  const setFonte = useCallback((tipo, dados) => {
    setState(prev => ({
      ...prev,
      fonte: { tipo, dados },
      etapasCompletas: new Set([...prev.etapasCompletas, 0]),
    }));
  }, []);

  const clearFonte = useCallback(() => {
    setState(prev => ({
      ...prev,
      fonte: { tipo: null, dados: null },
    }));
  }, []);

  // === Ações para Texto-Base (Etapa 2) ===
  const setBlocos = useCallback((blocos) => {
    setState(prev => ({
      ...prev,
      textoBase: {
        ...prev.textoBase,
        blocos,
        blocosSelecionados: new Set(blocos.map(b => b.id)),
      },
    }));
  }, []);

  const toggleBlocoSelecionado = useCallback((blocoId) => {
    setState(prev => {
      const newSet = new Set(prev.textoBase.blocosSelecionados);
      if (newSet.has(blocoId)) {
        newSet.delete(blocoId);
      } else {
        newSet.add(blocoId);
      }
      return {
        ...prev,
        textoBase: {
          ...prev.textoBase,
          blocosSelecionados: newSet,
        },
      };
    });
  }, []);

  const atualizarBloco = useCallback((blocoId, novoConteudo) => {
    setState(prev => ({
      ...prev,
      textoBase: {
        ...prev.textoBase,
        blocos: prev.textoBase.blocos.map(b =>
          b.id === blocoId ? { ...b, content: novoConteudo } : b
        ),
      },
    }));
  }, []);

  const setTextoCompleto = useCallback((texto) => {
    setState(prev => ({
      ...prev,
      textoBase: {
        ...prev.textoBase,
        textoCompleto: texto,
      },
    }));
  }, []);

  const setModoEdicao = useCallback((modo) => {
    setState(prev => ({
      ...prev,
      textoBase: {
        ...prev.textoBase,
        modoEdicao: modo,
      },
    }));
  }, []);

  const confirmarTextoBase = useCallback(() => {
    setState(prev => ({
      ...prev,
      etapasCompletas: new Set([...prev.etapasCompletas, 1]),
    }));
  }, []);

  // === Ações para Configurações (Etapa 3) ===
  const setConfiguracao = useCallback((campo, valor) => {
    setState(prev => ({
      ...prev,
      configuracoes: {
        ...prev.configuracoes,
        [campo]: valor,
      },
    }));
  }, []);

  const setConfiguracoes = useCallback((configs) => {
    setState(prev => ({
      ...prev,
      configuracoes: {
        ...prev.configuracoes,
        ...configs,
      },
    }));
  }, []);

  const adicionarCitacao = useCallback((citacao) => {
    setState(prev => ({
      ...prev,
      configuracoes: {
        ...prev.configuracoes,
        citacoes: [...prev.configuracoes.citacoes, citacao],
      },
    }));
  }, []);

  const removerCitacao = useCallback((index) => {
    setState(prev => ({
      ...prev,
      configuracoes: {
        ...prev.configuracoes,
        citacoes: prev.configuracoes.citacoes.filter((_, i) => i !== index),
      },
    }));
  }, []);

  const confirmarConfiguracoes = useCallback(() => {
    setState(prev => ({
      ...prev,
      etapasCompletas: new Set([...prev.etapasCompletas, 2]),
    }));
  }, []);

  // === Ações para Materiais Complementares ===
  const adicionarMaterial = useCallback((tipo, material) => {
    setState(prev => ({
      ...prev,
      materiaisComplementares: {
        ...prev.materiaisComplementares,
        [tipo]: [...prev.materiaisComplementares[tipo], material],
      },
    }));
  }, []);

  const removerMaterial = useCallback((tipo, index) => {
    setState(prev => ({
      ...prev,
      materiaisComplementares: {
        ...prev.materiaisComplementares,
        [tipo]: prev.materiaisComplementares[tipo].filter((_, i) => i !== index),
      },
    }));
  }, []);

  // === Ações para Resultado (Etapa 4) ===
  const setResultado = useCallback((resultado) => {
    setState(prev => ({
      ...prev,
      resultado: {
        ...resultado,
        geradoEm: new Date().toISOString(),
      },
      etapasCompletas: new Set([...prev.etapasCompletas, 3]),
    }));
  }, []);

  // === Navegação ===
  const setEtapaAtual = useCallback((etapa) => {
    setState(prev => ({
      ...prev,
      etapaAtual: etapa,
    }));
  }, []);

  const podeAvancar = useCallback((etapaAtual) => {
    return state.etapasCompletas.has(etapaAtual);
  }, [state.etapasCompletas]);

  // === Reset ===
  const resetFluxo = useCallback(() => {
    setState(initialState);
  }, []);

  // === Helpers ===
  const getTextoBaseParaGeracao = useCallback(() => {
    const { textoBase } = state;
    if (textoBase.modoEdicao === 'texto') {
      return textoBase.textoCompleto;
    }
    // Modo blocos: concatenar apenas os selecionados
    return textoBase.blocos
      .filter(b => textoBase.blocosSelecionados.has(b.id))
      .map(b => b.content)
      .join('\n\n');
  }, [state]);

  const getTotalPalavras = useCallback(() => {
    const texto = getTextoBaseParaGeracao();
    return texto.split(/\s+/).filter(Boolean).length;
  }, [getTextoBaseParaGeracao]);

  const getTotalMateriais = useCallback(() => {
    const { materiaisComplementares } = state;
    return (
      materiaisComplementares.links.length +
      materiaisComplementares.videos.length +
      materiaisComplementares.pdfs.length
    );
  }, [state]);

  // Valor do contexto memoizado
  const value = useMemo(
    () => ({
      // Estado
      ...state,

      // Ações Fonte
      setFonte,
      clearFonte,

      // Ações Texto-Base
      setBlocos,
      toggleBlocoSelecionado,
      atualizarBloco,
      setTextoCompleto,
      setModoEdicao,
      confirmarTextoBase,

      // Ações Configurações
      setConfiguracao,
      setConfiguracoes,
      adicionarCitacao,
      removerCitacao,
      confirmarConfiguracoes,

      // Ações Materiais
      adicionarMaterial,
      removerMaterial,

      // Ações Resultado
      setResultado,

      // Navegação
      setEtapaAtual,
      podeAvancar,

      // Reset
      resetFluxo,

      // Helpers
      getTextoBaseParaGeracao,
      getTotalPalavras,
      getTotalMateriais,
    }),
    [
      state,
      setFonte,
      clearFonte,
      setBlocos,
      toggleBlocoSelecionado,
      atualizarBloco,
      setTextoCompleto,
      setModoEdicao,
      confirmarTextoBase,
      setConfiguracao,
      setConfiguracoes,
      adicionarCitacao,
      removerCitacao,
      confirmarConfiguracoes,
      adicionarMaterial,
      removerMaterial,
      setResultado,
      setEtapaAtual,
      podeAvancar,
      resetFluxo,
      getTextoBaseParaGeracao,
      getTotalPalavras,
      getTotalMateriais,
    ]
  );

  return <CriarContext.Provider value={value}>{children}</CriarContext.Provider>;
};

CriarProvider.propTypes = {
  children: PropTypes.node.isRequired,
};
