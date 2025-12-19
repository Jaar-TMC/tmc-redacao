import TooltipEducativo from './TooltipEducativo';

/**
 * Storybook Stories para TooltipEducativo
 *
 * Este arquivo demonstra todos os estados e variações do componente.
 * Útil para desenvolvimento visual e documentação.
 */

export default {
  title: 'Criar/TooltipEducativo',
  component: TooltipEducativo,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
};

// Story básica
export const Basico = {
  args: {
    title: 'Título do Tooltip',
    icon: '📝',
    children: (
      <p>
        Este é um exemplo básico de tooltip educativo. Clique no ícone de
        ajuda para ver esta mensagem.
      </p>
    ),
  },
  render: (args) => (
    <div className="p-8">
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold">Campo de Exemplo</label>
        <TooltipEducativo {...args} />
      </div>
    </div>
  ),
};

// Com conteúdo rico
export const ConteudoRico = {
  args: {
    title: 'Orientação sobre o Lide',
    icon: '📝',
    children: (
      <>
        <p>
          O lide é o primeiro parágrafo da matéria - deve responder às
          perguntas: <strong>O quê? Quem? Quando? Onde? Por quê? Como?</strong>
        </p>
        <p>Indique qual ângulo você quer destacar:</p>
        <ul>
          <li>"Focar no impacto econômico para o cidadão"</li>
          <li>"Destacar a reação do mercado financeiro"</li>
          <li>"Priorizar as declarações do ministro"</li>
        </ul>
      </>
    ),
  },
  render: (args) => (
    <div className="p-8">
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold">Orientação do Lide</label>
        <TooltipEducativo {...args} />
      </div>
      <textarea
        className="w-full mt-2 p-3 border border-light-gray rounded-lg"
        placeholder="Ex: Focar no impacto econômico..."
        rows={3}
      />
    </div>
  ),
};

// Sem ícone
export const SemIcone = {
  args: {
    title: 'Ajuda sem Ícone',
    children: <p>Este tooltip não tem um ícone emoji.</p>,
  },
  render: (args) => (
    <div className="p-8">
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold">Campo</label>
        <TooltipEducativo {...args} />
      </div>
    </div>
  ),
};

// Posição direita
export const PosicaoDireita = {
  args: {
    title: 'Tooltip à Direita',
    icon: '➡️',
    position: 'right',
    children: <p>Este tooltip aparece à direita do botão.</p>,
  },
  render: (args) => (
    <div className="p-8 flex items-center justify-center min-h-[400px]">
      <div className="flex items-center gap-2">
        <label>Campo</label>
        <TooltipEducativo {...args} />
      </div>
    </div>
  ),
};

// Posição esquerda
export const PosicaoEsquerda = {
  args: {
    title: 'Tooltip à Esquerda',
    icon: '⬅️',
    position: 'left',
    children: <p>Este tooltip aparece à esquerda do botão.</p>,
  },
  render: (args) => (
    <div className="p-8 flex items-center justify-end min-h-[400px]">
      <div className="flex items-center gap-2">
        <TooltipEducativo {...args} />
        <label>Campo</label>
      </div>
    </div>
  ),
};

// Posição topo
export const PosicaoTopo = {
  args: {
    title: 'Tooltip no Topo',
    icon: '⬆️',
    position: 'top',
    children: <p>Este tooltip aparece acima do botão.</p>,
  },
  render: (args) => (
    <div className="p-8 flex items-end justify-center min-h-[400px]">
      <div className="flex flex-col items-center gap-2">
        <TooltipEducativo {...args} />
        <label>Campo</label>
      </div>
    </div>
  ),
};

// Posição baixo
export const PosicaoBaixo = {
  args: {
    title: 'Tooltip Embaixo',
    icon: '⬇️',
    position: 'bottom',
    children: <p>Este tooltip aparece abaixo do botão.</p>,
  },
  render: (args) => (
    <div className="p-8 flex items-start justify-center min-h-[400px]">
      <div className="flex flex-col items-center gap-2">
        <label>Campo</label>
        <TooltipEducativo {...args} />
      </div>
    </div>
  ),
};

// Posição automática
export const PosicaoAutomatica = {
  args: {
    title: 'Tooltip com Posição Automática',
    icon: '🎯',
    position: 'auto',
    children: (
      <p>
        Este tooltip calcula automaticamente a melhor posição para não sair da
        tela. Tente redimensionar a janela para ver o comportamento.
      </p>
    ),
  },
  render: (args) => (
    <div className="p-8">
      <div className="flex items-center gap-2">
        <label>Campo</label>
        <TooltipEducativo {...args} />
      </div>
    </div>
  ),
};

// Exemplo com código
export const ComCodigo = {
  args: {
    title: 'Declarações de Fontes',
    icon: '💬',
    children: (
      <>
        <p>
          Citações diretas de especialistas, autoridades ou envolvidos dão
          credibilidade e humanizam a matéria.
        </p>
        <p>
          <strong>Formato sugerido:</strong>
        </p>
        <code>Nome, cargo/função: 'Declaração entre aspas simples'</code>
        <p>
          <strong>Exemplo:</strong>
        </p>
        <p>
          "João Silva, economista da FGV: 'As medidas terão efeito positivo em
          até 6 meses'"
        </p>
      </>
    ),
  },
  render: (args) => (
    <div className="p-8">
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold">Declarações de Fontes</label>
        <TooltipEducativo {...args} />
      </div>
      <textarea
        className="w-full mt-2 p-3 border border-light-gray rounded-lg"
        placeholder="Adicione citações diretas..."
        rows={4}
      />
    </div>
  ),
};

// Lista complexa
export const ListaComplexa = {
  args: {
    title: 'Contexto Adicional',
    icon: 'ℹ️',
    children: (
      <>
        <p>
          Informações de background que a IA deve considerar mas que não estão
          no texto-base:
        </p>
        <ul>
          <li>
            <strong>Histórico do tema:</strong> "Essa é a terceira tentativa..."
          </li>
          <li>
            <strong>Nuances políticas:</strong> "O partido X é contra..."
          </li>
          <li>
            <strong>Dados complementares:</strong> "Segundo o IBGE..."
          </li>
          <li>
            <strong>Conexões com outros fatos:</strong> "Isso se relaciona
            com..."
          </li>
        </ul>
      </>
    ),
  },
  render: (args) => (
    <div className="p-8">
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold">Contexto Adicional</label>
        <TooltipEducativo {...args} />
      </div>
      <textarea
        className="w-full mt-2 p-3 border border-light-gray rounded-lg"
        placeholder="Adicione contexto que não está no texto-base..."
        rows={4}
      />
    </div>
  ),
};

// Todos os ícones de ajuda do planejamento
export const TodosIcones = {
  render: () => (
    <div className="p-8 space-y-6 max-w-2xl">
      <h2 className="text-xl font-bold">Todos os Tooltips do Planejamento</h2>

      {/* Data de Publicação */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Data de Publicação</label>
        <TooltipEducativo
          title="Data de Publicação"
          icon="📅"
          position="right"
        >
          <p>
            Quando o conteúdo original foi publicado ou quando o evento
            aconteceu. Isso ajuda a IA a contextualizar temporalmente.
          </p>
        </TooltipEducativo>
      </div>

      {/* Orientação do Lide */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Orientação do Lide</label>
        <TooltipEducativo
          title="Orientação sobre o Lide"
          icon="📝"
          position="right"
        >
          <p>O lide é o primeiro parágrafo da matéria...</p>
        </TooltipEducativo>
      </div>

      {/* Declarações de Fontes */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Declarações de Fontes</label>
        <TooltipEducativo
          title="Declarações de Fontes"
          icon="💬"
          position="right"
        >
          <p>Citações diretas de especialistas...</p>
        </TooltipEducativo>
      </div>

      {/* Contexto Adicional */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Contexto Adicional</label>
        <TooltipEducativo
          title="Contexto Adicional"
          icon="ℹ️"
          position="right"
        >
          <p>Informações de background...</p>
        </TooltipEducativo>
      </div>

      {/* Créditos */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Créditos</label>
        <TooltipEducativo
          title="Créditos a Instituições"
          icon="🏛️"
          position="right"
        >
          <p>Alguns conteúdos exigem atribuição obrigatória...</p>
        </TooltipEducativo>
      </div>

      {/* Persona */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Persona</label>
        <TooltipEducativo
          title="Persona da Matéria"
          icon="👤"
          position="right"
        >
          <p>Define a "voz" e abordagem do texto...</p>
        </TooltipEducativo>
      </div>

      {/* Tom */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Tom</label>
        <TooltipEducativo title="Tom da Escrita" icon="🎭" position="right">
          <p>O tom afeta a escolha de palavras...</p>
        </TooltipEducativo>
      </div>

      {/* Instruções */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Instruções para IA</label>
        <TooltipEducativo
          title="Instruções Adicionais"
          icon="✍️"
          position="right"
        >
          <p>Comandos específicos para a IA seguir...</p>
        </TooltipEducativo>
      </div>

      {/* Link */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Link Complementar</label>
        <TooltipEducativo
          title="Link Complementar (WEB)"
          icon="🔗"
          position="right"
        >
          <p>Adicione links de páginas que complementam a matéria...</p>
        </TooltipEducativo>
      </div>

      {/* Vídeo */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Vídeo YouTube</label>
        <TooltipEducativo
          title="Vídeo do YouTube"
          icon="▶️"
          position="right"
        >
          <p>Adicione um vídeo complementar ao texto-base...</p>
        </TooltipEducativo>
      </div>

      {/* PDF */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-semibold w-48">Arquivo PDF</label>
        <TooltipEducativo title="Arquivo PDF" icon="📎" position="right">
          <p>Anexe documentos PDF como fonte adicional...</p>
        </TooltipEducativo>
      </div>
    </div>
  ),
};

// Responsividade
export const Responsivo = {
  args: {
    title: 'Tooltip Responsivo',
    icon: '📱',
    position: 'auto',
    children: (
      <p>
        Este tooltip se adapta ao tamanho da tela. Em mobile (largura menor que
        768px), sempre aparece embaixo do elemento.
      </p>
    ),
  },
  render: (args) => (
    <div className="p-8">
      <div className="flex items-center gap-2">
        <label>Campo</label>
        <TooltipEducativo {...args} />
      </div>
      <p className="mt-4 text-sm text-medium-gray">
        Redimensione a janela para ver o comportamento responsivo.
      </p>
    </div>
  ),
};
