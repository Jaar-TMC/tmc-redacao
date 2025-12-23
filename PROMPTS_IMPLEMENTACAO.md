# PROMPTS ESPECIALIZADOS PARA IMPLEMENTAÇÃO - TMC Redação

**Objetivo:** Prompts otimizados para vibe coding com IA, minimizando alucinações
**Metodologia:** Cada prompt inclui contexto completo, código existente e resultado esperado

---

## PRINCÍPIOS DOS PROMPTS

1. **Contexto primeiro** - Sempre fornecer o código existente
2. **Resultado específico** - Mostrar exatamente o que deve mudar
3. **Sem ambiguidade** - Usar nomes exatos de variáveis e funções
4. **Limitações claras** - Dizer o que NÃO deve ser alterado
5. **Validação inclusa** - Incluir como testar se funcionou

---

# FASE 1: BUGS CRÍTICOS (P0)

---

## PROMPT 1.1: Integrar ConfigurarPage com CriarContext

```
CONTEXTO DO PROJETO:
- App React com Vite + TailwindCSS
- Fluxo de criação de matérias jornalísticas em 4 etapas
- Arquivo: src/pages/criar/ConfigurarPage.jsx (702 linhas)
- Context: src/context/CriarContext.jsx

PROBLEMA ATUAL:
O ConfigurarPage usa useState local para todos os campos, mas não persiste os dados no CriarContext. Quando o usuário navega para a próxima página e volta, perde tudo.

CÓDIGO EXISTENTE DO CONTEXT (funções disponíveis):
```javascript
// Já existe no CriarContext:
setConfiguracoes(configs)  // Recebe objeto com todas as configs
setConfiguracao(campo, valor)  // Atualiza campo individual
adicionarMaterial(tipo, material)  // tipo: 'links' | 'videos' | 'pdfs'
removerMaterial(tipo, index)
confirmarConfiguracoes()  // Marca etapa como completa
```

ESTADOS LOCAIS ATUAIS NO ConfigurarPage (linhas 207-223):
```javascript
const [dataPublicacao, setDataPublicacao] = useState('');
const [orientacaoLide, setOrientacaoLide] = useState('');
const [citacoes, setCitacoes] = useState([]);
const [contextoAdicional, setContextoAdicional] = useState('');
const [precisaCredito, setPrecisaCredito] = useState(false);
const [creditoSelecionado, setCreditoSelecionado] = useState('');
const [persona, setPersona] = useState('jornalista');
const [tom, setTom] = useState('formal');
const [instrucoes, setInstrucoes] = useState('');
const [links, setLinks] = useState([]);
const [videos, setVideos] = useState([]);
const [pdfs, setPdfs] = useState([]);
```

ESTRUTURA ESPERADA NO CONTEXT:
```javascript
configuracoes: {
  data: string,
  orientacaoLide: string,
  citacoes: Array<{id: number, text: string}>,
  contexto: string,
  creditos: string,
  persona: 'jornalista' | 'especialista' | 'colunista' | 'influencer',
  tom: 'formal' | 'informal' | 'tecnico' | 'persuasivo' | 'neutro',
  instrucoes: string,
}

materiaisComplementares: {
  links: Array<{id: number, url: string, status: string}>,
  videos: Array<{id: number, url: string, status: string}>,
  pdfs: Array<{id: number, name: string, size: number, status: string}>,
}
```

TAREFA:
1. Importar useCriar no ConfigurarPage
2. Inicializar estados locais com valores do context (para quando usuário voltar)
3. Criar useEffect que sincroniza estados locais com o context
4. No botão "Revisar e Gerar", chamar confirmarConfiguracoes() antes de navigate

RESULTADO ESPERADO:
- Usuário preenche campos
- Navega para /criar/revisar
- Volta para /criar/configurar
- Campos permanecem preenchidos

NÃO ALTERAR:
- Estrutura visual/JSX do componente
- Handlers individuais (handleAddCitacao, etc.)
- Tooltips e opções estáticas

COMO TESTAR:
1. Preencher todos os campos
2. Clicar "Revisar e Gerar"
3. Clicar "Voltar"
4. Verificar se campos mantêm valores
```

---

## PROMPT 1.2: Integrar RevisarPage com dados reais do Context

```
CONTEXTO DO PROJETO:
- App React com fluxo de criação de matérias
- Arquivo: src/pages/criar/RevisarPage.jsx
- Context: src/context/CriarContext.jsx

PROBLEMA ATUAL:
RevisarPage usa mockReviewData hardcoded ao invés de ler dados reais do CriarContext.

MOCK DATA ATUAL (a ser removido):
```javascript
const mockReviewData = {
  textoBase: {
    title: 'Texto Principal',
    content: 'Lorem ipsum...',
    words: 450,
    source: 'Matérias do Feed'
  },
  materiais: [
    { type: 'link', title: 'Notícia relacionada...', words: 280, status: 'extracted' },
    { type: 'video', title: 'Entrevista no YouTube...', words: 520, status: 'extracted' },
  ],
  configuracoes: {
    persona: 'Jornalista Imparcial',
    tom: 'Formal',
    lide: 'Focar no impacto econômico...',
    citacoes: 2,
  }
};
```

DADOS DISPONÍVEIS NO CONTEXT:
```javascript
const {
  fonte,                    // { tipo: string, dados: any }
  textoBase,               // { blocos: [], textoCompleto: '', blocosSelecionados: Set }
  configuracoes,           // { data, orientacaoLide, citacoes, contexto, creditos, persona, tom, instrucoes }
  materiaisComplementares, // { links: [], videos: [], pdfs: [] }
  getTextoBaseParaGeracao, // () => string (texto concatenado)
  getTotalPalavras,        // () => number
  getTotalMateriais,       // () => number
} = useCriar();
```

TAREFA:
1. Remover mockReviewData completamente
2. Importar e usar useCriar()
3. Construir dados de exibição a partir do context real
4. Mapear persona ID para label legível (usar personaOptions do ConfigurarPage)
5. Mapear tom ID para label legível

MAPEAMENTOS NECESSÁRIOS:
```javascript
const personaLabels = {
  'jornalista': 'Jornalista Imparcial',
  'especialista': 'Especialista',
  'colunista': 'Colunista',
  'influencer': 'Influencer'
};

const tomLabels = {
  'formal': 'Formal',
  'informal': 'Informal',
  'tecnico': 'Técnico',
  'persuasivo': 'Persuasivo',
  'neutro': 'Neutro'
};

const fonteLabels = {
  'feed': 'Matérias do Feed',
  'video': 'Transcrição de Vídeo',
  'tema': 'Tema em Alta',
  'link': 'Link da Web'
};
```

RESULTADO ESPERADO:
- Página mostra texto-base real selecionado pelo usuário
- Mostra configurações reais (persona, tom, lide, citações)
- Mostra materiais complementares reais (links, vídeos, PDFs)
- Contagem de palavras é calculada dinamicamente

NÃO ALTERAR:
- Animação de geração (progress bar, mensagens)
- Layout e estrutura visual
- Lógica de expansão dos cards

COMO TESTAR:
1. Passar pelas etapas 1, 2 e 3 preenchendo dados
2. Chegar na RevisarPage
3. Verificar se dados mostrados correspondem ao que foi preenchido
```

---

## PROMPT 1.3: Preparar estrutura para API de geração (sem backend ainda)

```
CONTEXTO DO PROJETO:
- Front-end React que futuramente chamará API de geração de texto com IA
- Arquivo: src/pages/criar/RevisarPage.jsx
- Atualmente a geração é 100% simulada com setTimeout

CÓDIGO ATUAL DA GERAÇÃO (simulado):
```javascript
const handleGenerate = () => {
  setIsGenerating(true);
  setProgress(0);

  const interval = setInterval(() => {
    setProgress(prev => {
      const increment = Math.random() * 15 + 5;
      const newProgress = Math.min(prev + increment, 100);

      if (newProgress >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          navigate('/criar/editor');
        }, 500);
      }

      return newProgress;
    });
  }, 800);
};
```

TAREFA:
Refatorar handleGenerate para:
1. Manter a animação visual atual (UX não muda)
2. Preparar payload com todos os dados necessários para API
3. Adicionar try/catch com tratamento de erro
4. Usar flag de ambiente para alternar entre mock e API real
5. Ao finalizar (mock ou real), salvar resultado no context via setResultado()

PAYLOAD ESPERADO PARA API:
```javascript
const payload = {
  textoBase: getTextoBaseParaGeracao(), // string
  fonte: {
    tipo: fonte.tipo,
    // dados específicos se necessário
  },
  configuracoes: {
    data: configuracoes.data,
    orientacaoLide: configuracoes.orientacaoLide,
    citacoes: configuracoes.citacoes.map(c => c.text),
    contexto: configuracoes.contexto,
    creditos: configuracoes.creditos,
    persona: configuracoes.persona,
    tom: configuracoes.tom,
    instrucoes: configuracoes.instrucoes,
  },
  materiaisComplementares: {
    links: materiaisComplementares.links.map(l => l.url),
    videos: materiaisComplementares.videos.map(v => v.url),
    pdfs: materiaisComplementares.pdfs.map(p => ({ name: p.name, size: p.size })),
  }
};
```

ESTRUTURA DO RESULTADO (mock por enquanto):
```javascript
const mockResultado = {
  titulo: 'Título gerado pela IA',
  conteudo: `
    <h2>Lide da matéria</h2>
    <p>Primeiro parágrafo com as informações principais...</p>
    <h2>Desenvolvimento</h2>
    <p>Corpo da matéria...</p>
  `,
};
```

IMPLEMENTAÇÃO ESPERADA:
```javascript
const handleGenerate = async () => {
  setIsGenerating(true);
  setProgress(0);

  // Preparar payload
  const payload = { /* estrutura acima */ };

  // Log para debug (remover em produção)
  console.log('Payload para geração:', payload);

  try {
    // Flag para alternar entre mock e API real
    const USE_MOCK = true; // Mudar para false quando API estiver pronta

    if (USE_MOCK) {
      // Simular progresso (manter UX atual)
      await simulateProgress();

      // Mock do resultado
      const mockResultado = { /* ... */ };
      setResultado(mockResultado);
    } else {
      // Chamada real para API (futuro)
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error('Erro na geração');

      const data = await response.json();
      setResultado(data);
    }

    navigate('/criar/editor');
  } catch (error) {
    console.error('Erro na geração:', error);
    setIsGenerating(false);
    // TODO: Mostrar toast de erro
  }
};

// Extrair simulação de progresso para função separada
const simulateProgress = () => {
  return new Promise((resolve) => {
    let currentProgress = 0;
    const interval = setInterval(() => {
      const increment = Math.random() * 15 + 5;
      currentProgress = Math.min(currentProgress + increment, 100);
      setProgress(currentProgress);

      if (currentProgress >= 100) {
        clearInterval(interval);
        setTimeout(resolve, 500);
      }
    }, 800);
  });
};
```

NÃO ALTERAR:
- Mensagens de progresso (generationMessages)
- Visual da animação
- Estrutura do JSX

COMO TESTAR:
1. Abrir console do navegador
2. Clicar em "GERAR MATÉRIA"
3. Verificar se payload aparece no console com dados corretos
4. Verificar se navegação para /criar/editor acontece após animação
```

---

# FASE 2: ALTA PRIORIDADE (P1)

---

## PROMPT 2.1: Unificar fluxos de criação (deprecar rotas antigas)

```
CONTEXTO DO PROJETO:
- App.jsx contém todas as rotas
- Existem dois fluxos de criação que confundem o usuário
- Header.jsx tem dropdown "Criar" que aponta para rotas antigas

ROTAS ATUAIS:
```javascript
// FLUXO NOVO (correto):
/criar              → SelecionarFontePage
/criar/texto-base   → TextoBasePage
/criar/configurar   → ConfigurarPage
/criar/revisar      → RevisarPage
/criar/editor       → CriarPostPage

// FLUXO ANTIGO (a deprecar):
/selecionar-tema    → SelecionarTemaPage
/criar-inspiracao   → CriarInspiracaoPage
```

HEADER.JSX - DROPDOWN CRIAR (código atual):
```javascript
const criarOptions = [
  { label: 'Do Zero', href: '/criar', icon: <Edit3 size={16} /> },
  { label: 'Com Inspiração', href: '/criar-inspiracao', icon: <Lightbulb size={16} /> },
  { label: 'Transcrever Vídeo', href: '/transcricao', icon: <Video size={16} /> },
];
```

TAREFA:
1. No App.jsx: Criar redirects das rotas antigas para as novas
2. No Header.jsx: Atualizar dropdown para usar apenas rotas novas
3. Manter página de transcrição (/transcricao) se existir

RESULTADO ESPERADO NO APP.JSX:
```javascript
// Redirects (adicionar antes das rotas normais)
<Route path="/criar-inspiracao" element={<Navigate to="/criar" replace />} />
<Route path="/selecionar-tema" element={<Navigate to="/criar" replace />} />
```

RESULTADO ESPERADO NO HEADER.JSX:
```javascript
const criarOptions = [
  { label: 'Nova Matéria', href: '/criar', icon: <Edit3 size={16} /> },
  { label: 'Transcrever Vídeo', href: '/transcricao', icon: <Video size={16} /> },
];
// Remover opção "Com Inspiração" pois agora está integrada no fluxo /criar
```

NÃO ALTERAR:
- Estrutura visual do Header
- Lógica do dropdown
- Outras rotas não relacionadas

COMO TESTAR:
1. Acessar /criar-inspiracao → deve redirecionar para /criar
2. Acessar /selecionar-tema → deve redirecionar para /criar
3. Dropdown "Criar" deve mostrar apenas "Nova Matéria" e "Transcrever Vídeo"
```

---

## PROMPT 2.2: Corrigir FAB mobile no ActionPanel

```
CONTEXTO:
- ActionPanel.jsx é o painel lateral de matérias selecionadas
- Em mobile, aparece como bottom sheet com FAB (floating action button)
- Bug: FAB não abre o painel quando clicado

CÓDIGO ATUAL COM BUG (linha ~149):
```javascript
<button
  onClick={() => !isOpen && onClose?.()}  // BUG: lógica invertida
  className="fixed bottom-6 right-6 lg:hidden z-40 bg-tmc-orange text-white p-4 rounded-full shadow-lg"
>
  <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">
    {selectedCount}
  </span>
  <List size={24} />
</button>
```

PROBLEMA:
- `onClose` deveria ser `onOpen`
- A lógica `!isOpen && onClose` não faz sentido

CORREÇÃO ESPERADA:
```javascript
<button
  onClick={() => !isOpen && onOpen?.()}  // CORRETO: abre quando fechado
  className="fixed bottom-6 right-6 lg:hidden z-40 bg-tmc-orange text-white p-4 rounded-full shadow-lg"
  aria-label={`Abrir painel com ${selectedCount} matérias selecionadas`}
>
  ...
</button>
```

VERIFICAR TAMBÉM:
- Se onOpen está sendo passado como prop para o componente
- Se o componente pai (RedacaoPage) passa onOpen corretamente

COMO TESTAR:
1. Abrir app em viewport mobile (< 1024px)
2. Selecionar algumas matérias
3. Clicar no FAB laranja no canto inferior direito
4. Painel deve abrir mostrando matérias selecionadas
```

---

## PROMPT 2.3: Tornar Texto Completo editável

```
CONTEXTO:
- Arquivo: src/pages/criar/variantes/TextoBaseFeed.jsx
- Componente permite alternar entre visualização de "Tópicos" e "Texto Completo"
- Bug: textarea do Texto Completo tem onChange vazio

CÓDIGO ATUAL COM BUG (linha ~329):
```javascript
<textarea
  value={currentMateria?.fullText || ''}
  onChange={() => {}}  // BUG: handler vazio
  className="w-full h-64 px-4 py-3 border border-light-gray rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-tmc-orange/50"
  placeholder="Texto completo da matéria..."
/>
```

ESTRUTURA DE DADOS ATUAL:
```javascript
// materias é um array de objetos com esta estrutura:
{
  id: string,
  title: string,
  source: string,
  favicon: string,
  fullText: string,      // <- Este campo precisa ser editável
  topics: Array<Topic>,
  url: string
}
```

TAREFA:
1. Criar estado local para armazenar edições: `editedFullText`
2. Implementar onChange que atualiza o estado
3. Usar valor editado se existir, senão usar original
4. Propagar mudanças para o contexto via callback

IMPLEMENTAÇÃO ESPERADA:
```javascript
// Adicionar estado para edições
const [editedFullText, setEditedFullText] = useState({});

// Função para obter texto (editado ou original)
const getFullText = (materiaId) => {
  return editedFullText[materiaId] ?? materias.find(m => m.id === materiaId)?.fullText ?? '';
};

// Handler de mudança
const handleFullTextChange = (materiaId, newText) => {
  setEditedFullText(prev => ({
    ...prev,
    [materiaId]: newText
  }));

  // Opcional: propagar para parent/context
  onDataChange?.({
    type: 'fullTextEdit',
    materiaId,
    newText
  });
};

// No JSX:
<textarea
  value={getFullText(currentMateria?.id)}
  onChange={(e) => handleFullTextChange(currentMateria?.id, e.target.value)}
  className="..."
/>
```

NÃO ALTERAR:
- Lógica de tópicos (TopicCard)
- Tabs de alternância
- Layout geral

COMO TESTAR:
1. Selecionar matérias e ir para TextoBasePage
2. Alternar para tab "Texto Completo"
3. Editar o texto
4. Alternar para outra matéria e voltar
5. Edições devem persistir
```

---

## PROMPT 2.4: Corrigir link "Ver original"

```
CONTEXTO:
- Arquivo: src/pages/criar/variantes/TextoBaseFeed.jsx
- Link "Ver original" está hardcoded como href="#"

CÓDIGO ATUAL COM BUG:
```javascript
<a
  href="#"  // BUG: deveria usar URL real
  className="text-xs text-tmc-orange hover:underline flex items-center gap-1"
>
  Ver original
  <ExternalLink size={12} />
</a>
```

DADOS DISPONÍVEIS:
```javascript
// currentMateria tem esta estrutura (vem do mockData/feed):
{
  id: string,
  title: string,
  source: string,
  favicon: string,
  fullText: string,
  topics: Array,
  url: string  // <- URL real da matéria original
}
```

CORREÇÃO ESPERADA:
```javascript
<a
  href={currentMateria?.url || '#'}
  target="_blank"
  rel="noopener noreferrer"
  className="text-xs text-tmc-orange hover:underline flex items-center gap-1"
  onClick={(e) => e.stopPropagation()}  // Evitar conflito com seleção
>
  Ver original
  <ExternalLink size={12} />
</a>
```

COMO TESTAR:
1. Ir para TextoBasePage com matérias selecionadas
2. Clicar em "Ver original"
3. Deve abrir URL da matéria em nova aba
```

---

# FASE 3: MÉDIA PRIORIDADE (P2)

---

## PROMPT 3.1: Adicionar validação de URLs

```
CONTEXTO:
- Arquivo: src/pages/criar/ConfigurarPage.jsx
- Campos de link e vídeo aceitam qualquer string
- Necessário validar formato de URL

CÓDIGO ATUAL (sem validação):
```javascript
const handleAddLink = useCallback(() => {
  if (novoLink.trim()) {
    setLinks(prev => [...prev, { id: Date.now(), url: novoLink.trim(), status: 'pending' }]);
    setNovoLink('');
  }
}, [novoLink]);
```

TAREFA:
1. Criar função de validação de URL genérica
2. Criar função de validação específica para YouTube
3. Mostrar feedback visual de erro
4. Impedir adição de URLs inválidas

IMPLEMENTAÇÃO ESPERADA:
```javascript
// Funções de validação
const isValidUrl = (string) => {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
};

const isValidYoutubeUrl = (string) => {
  if (!isValidUrl(string)) return false;
  const patterns = [
    /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/,
    /^https?:\/\/youtu\.be\/[\w-]+/,
    /^https?:\/\/(www\.)?youtube\.com\/embed\/[\w-]+/,
  ];
  return patterns.some(pattern => pattern.test(string));
};

// Estado para erros
const [linkError, setLinkError] = useState('');
const [videoError, setVideoError] = useState('');

// Handler atualizado
const handleAddLink = useCallback(() => {
  if (!novoLink.trim()) return;

  if (!isValidUrl(novoLink.trim())) {
    setLinkError('URL inválida. Use formato: https://exemplo.com');
    return;
  }

  setLinkError('');
  setLinks(prev => [...prev, { id: Date.now(), url: novoLink.trim(), status: 'pending' }]);
  setNovoLink('');
}, [novoLink]);

const handleAddVideo = useCallback(() => {
  if (!novoVideo.trim()) return;

  if (!isValidYoutubeUrl(novoVideo.trim())) {
    setVideoError('URL inválida. Use link do YouTube (youtube.com ou youtu.be)');
    return;
  }

  setVideoError('');
  setVideos(prev => [...prev, { id: Date.now(), url: novoVideo.trim(), status: 'pending' }]);
  setNovoVideo('');
}, [novoVideo]);
```

JSX PARA MOSTRAR ERRO:
```javascript
{linkError && (
  <p className="text-xs text-red-500 mt-1">{linkError}</p>
)}
```

COMO TESTAR:
1. Digitar "texto qualquer" no campo de link → deve mostrar erro
2. Digitar "https://exemplo.com" → deve adicionar
3. Digitar "youtube.com/watch" no campo de vídeo → deve mostrar erro (falta https)
4. Digitar "https://youtube.com/watch?v=abc123" → deve adicionar
```

---

## PROMPT 3.2: Validação de tamanho de PDF

```
CONTEXTO:
- Arquivo: src/pages/criar/ConfigurarPage.jsx
- Tooltip diz "Máximo: 50 páginas ou 10MB" mas não há validação

CÓDIGO ATUAL (sem validação):
```javascript
const handleFileUpload = useCallback((e) => {
  const files = Array.from(e.target.files || []);
  const newPdfs = files.map(file => ({
    id: Date.now() + Math.random(),
    name: file.name,
    size: file.size,
    status: 'uploaded'
  }));
  setPdfs(prev => [...prev, ...newPdfs]);
}, []);
```

IMPLEMENTAÇÃO ESPERADA:
```javascript
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB em bytes

const [pdfError, setPdfError] = useState('');

const handleFileUpload = useCallback((e) => {
  const files = Array.from(e.target.files || []);
  setPdfError('');

  const validFiles = [];
  const errors = [];

  files.forEach(file => {
    // Validar tipo
    if (file.type !== 'application/pdf') {
      errors.push(`${file.name}: Apenas arquivos PDF são aceitos`);
      return;
    }

    // Validar tamanho
    if (file.size > MAX_FILE_SIZE) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      errors.push(`${file.name}: Arquivo muito grande (${sizeMB}MB). Máximo: 10MB`);
      return;
    }

    validFiles.push({
      id: Date.now() + Math.random(),
      name: file.name,
      size: file.size,
      file: file,  // Guardar referência para upload futuro
      status: 'uploaded'
    });
  });

  if (errors.length > 0) {
    setPdfError(errors.join('\n'));
  }

  if (validFiles.length > 0) {
    setPdfs(prev => [...prev, ...validFiles]);
  }

  // Limpar input para permitir reselecionar mesmo arquivo
  e.target.value = '';
}, []);
```

JSX PARA MOSTRAR ERRO:
```javascript
{pdfError && (
  <div className="text-xs text-red-500 mt-1 whitespace-pre-line">
    {pdfError}
  </div>
)}
```

COMO TESTAR:
1. Tentar anexar arquivo .docx → deve mostrar erro de tipo
2. Tentar anexar PDF de 15MB → deve mostrar erro de tamanho
3. Anexar PDF de 5MB → deve adicionar normalmente
```

---

## PROMPT 3.3: Corrigir Stepper na RevisarPage

```
CONTEXTO:
- Arquivo: src/pages/criar/RevisarPage.jsx
- Stepper mostra step errado (2 ao invés de 3)

CÓDIGO ATUAL:
```javascript
<Stepper
  steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
  currentStep={2}  // BUG: deveria ser 3 (ou alterar steps)
  onStepClick={handleStepClick}
/>
```

OPÇÃO 1 - Adicionar step "Revisar":
```javascript
<Stepper
  steps={['Fonte', 'Texto-Base', 'Configurar', 'Revisar', 'Editor']}
  currentStep={3}
  onStepClick={handleStepClick}
/>
```

OPÇÃO 2 - Manter 4 steps, ajustar índice:
Considerar que "Revisar" faz parte de "Configurar" e ir para 3 (Editor)
```javascript
<Stepper
  steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
  currentStep={3}  // Indica que está entre Configurar e Editor
  onStepClick={handleStepClick}
/>
```

RECOMENDAÇÃO:
Usar Opção 1 para deixar claro que é uma etapa distinta.

COMO TESTAR:
1. Navegar até RevisarPage
2. Stepper deve mostrar "Revisar" como etapa atual (destacada)
3. Steps anteriores devem ser clicáveis para voltar
```

---

# FASE 4: BAIXA PRIORIDADE (P3)

---

## PROMPT 4.1: Persistência com localStorage

```
CONTEXTO:
- Arquivo: src/context/CriarContext.jsx
- Estado se perde ao recarregar página

TAREFA:
Implementar persistência automática no localStorage.

IMPLEMENTAÇÃO ESPERADA:
```javascript
// Chave para localStorage
const STORAGE_KEY = 'tmc-criar-state';

// Função para serializar (Sets não são JSON-serializáveis)
const serializeState = (state) => {
  return JSON.stringify({
    ...state,
    textoBase: {
      ...state.textoBase,
      blocosSelecionados: Array.from(state.textoBase.blocosSelecionados),
    },
    etapasCompletas: Array.from(state.etapasCompletas),
  });
};

// Função para deserializar
const deserializeState = (json) => {
  try {
    const parsed = JSON.parse(json);
    return {
      ...parsed,
      textoBase: {
        ...parsed.textoBase,
        blocosSelecionados: new Set(parsed.textoBase.blocosSelecionados),
      },
      etapasCompletas: new Set(parsed.etapasCompletas),
    };
  } catch {
    return initialState;
  }
};

// Carregar estado inicial do localStorage
const loadInitialState = () => {
  if (typeof window === 'undefined') return initialState;
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved ? deserializeState(saved) : initialState;
};

// No CriarProvider:
export const CriarProvider = ({ children }) => {
  const [state, setState] = useState(loadInitialState);

  // Salvar no localStorage quando estado mudar
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, serializeState(state));
  }, [state]);

  // Limpar ao resetar
  const resetFluxo = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setState(initialState);
  }, []);

  // ... resto do código
};
```

COMO TESTAR:
1. Preencher etapas 1 e 2
2. Recarregar página (F5)
3. Estado deve ser restaurado
4. Clicar em "Resetar" deve limpar tudo
```

---

## PROMPT 4.2: Footer stats dinâmico

```
CONTEXTO:
- Arquivo: src/components/layout/ActionPanel.jsx
- Footer mostra "156 matérias coletadas hoje" hardcoded

CÓDIGO ATUAL:
```javascript
<p className="text-xs text-medium-gray">
  156 matérias coletadas hoje
</p>
```

OPÇÃO 1 - Receber como prop:
```javascript
// ActionPanel.jsx
const ActionPanel = ({
  selectedArticles,
  onRemove,
  onRemoveAll,
  onCreate,
  totalMateriasHoje = 0,  // Nova prop
  ...
}) => {
  return (
    // ...
    <p className="text-xs text-medium-gray">
      {totalMateriasHoje} matérias coletadas hoje
    </p>
  );
};
```

OPÇÃO 2 - Calcular do mockData (temporário):
```javascript
import { articles } from '../../data/mockData';

// No componente:
const totalMateriasHoje = useMemo(() => {
  const hoje = new Date().toDateString();
  return articles.filter(a =>
    new Date(a.publishedAt).toDateString() === hoje
  ).length;
}, []);
```

RECOMENDAÇÃO:
Usar Opção 1, passando valor do backend quando disponível.
```

---

## PROMPT 4.3: Implementar prefers-reduced-motion

```
CONTEXTO:
- Várias animações no app (transições, loading, etc.)
- Usuários com sensibilidade a movimento podem ter problemas

TAREFA:
Respeitar preferência do sistema operacional.

IMPLEMENTAÇÃO CSS (adicionar ao globals.css ou tailwind):
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

PARA ANIMAÇÕES JS (RevisarPage progress):
```javascript
// Hook para detectar preferência
const usePrefersReducedMotion = () => {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handler = (e) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return prefersReducedMotion;
};

// No componente:
const prefersReducedMotion = usePrefersReducedMotion();

const simulateProgress = () => {
  if (prefersReducedMotion) {
    // Pular animação, ir direto para 100%
    setProgress(100);
    return Promise.resolve();
  }

  // Animação normal
  return new Promise((resolve) => {
    // ... código existente
  });
};
```

COMO TESTAR:
1. No Windows: Configurações > Acessibilidade > Efeitos visuais > Desligar animações
2. No Mac: Preferências do Sistema > Acessibilidade > Exibição > Reduzir movimento
3. Recarregar app e verificar que animações são instantâneas
```

---

# DICAS GERAIS PARA VIBE CODING

## Antes de cada prompt:
1. Ler o arquivo atual completo
2. Identificar imports existentes
3. Verificar estrutura de dados usada

## Durante a implementação:
1. Fazer uma mudança de cada vez
2. Testar após cada mudança
3. Commitar incrementalmente

## Formato ideal de prompt:
```
CONTEXTO: [arquivo, linha, problema]
CÓDIGO ATUAL: [snippet exato]
TAREFA: [o que fazer, específico]
RESULTADO ESPERADO: [código final]
NÃO ALTERAR: [proteções]
COMO TESTAR: [passos de verificação]
```

---

**Documento gerado em:** 23/12/2025
**Próximo passo:** Executar prompts na ordem do roadmap
