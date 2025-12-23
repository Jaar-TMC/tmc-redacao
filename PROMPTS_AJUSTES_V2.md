# PROMPTS ESPECIALIZADOS - AJUSTES V2

**Data:** 23/12/2025
**Baseado em:** Revisão e testes do app pelo usuário
**Objetivo:** Prompts otimizados para implementar os ajustes identificados

---

## RESUMO DOS AJUSTES

| # | Prioridade | Descrição | Arquivo Principal |
|---|------------|-----------|-------------------|
| 1 | Baixa | Remover subheader da tela de transcrição | TranscricaoPage.jsx |
| 2 | Baixa | Remover ícone do título "Matérias sobre tema" | TextoBaseTema.jsx |
| 3 | Média | Adicionar botão "Ir direto ao editor" no ponto de partida | criar/index.jsx |
| 4 | Alta | "Adicionar mais matérias" deve mostrar lista, não redirecionar | TextoBaseFeed.jsx |
| 5 | Alta | Fluxo de tema: se selecionar matérias, ir para tela de edição | TextoBaseTema.jsx + TextoBasePage.jsx |

---

# PROMPT 1: Remover subheader da tela de transcrição

```
CONTEXTO DO PROJETO:
- App React com Vite + TailwindCSS
- Arquivo: src/pages/transcricao/TranscricaoPage.jsx (294 linhas)
- Componente: StepIndicator mostra "1 Adicionar Vídeo" e "2 Transcrevendo"

PROBLEMA:
O usuário não quer o subheader com os steps na tela de transcrição.

CÓDIGO ATUAL (linhas 185-195):
```jsx
{/* Step Indicator */}
<div className="hidden md:block">
  <StepIndicator steps={STEPS} currentStep={currentStep} />
</div>
</div>

{/* Step Indicator Mobile */}
<div className="md:hidden mt-4">
  <StepIndicator steps={STEPS} currentStep={currentStep} />
</div>
```

TAMBÉM REMOVER (linhas 19-23):
```jsx
// Etapas do fluxo (simplificado)
const STEPS = [
  { id: 'input', label: 'Adicionar Vídeo' },
  { id: 'transcribing', label: 'Transcrevendo' }
];
```

E O IMPORT (linha 14):
```jsx
import {
  YouTubeInput,
  VideoPreview,
  ProgressOverlay,
  StepIndicator  // <- REMOVER
} from './components';
```

TAREFA:
1. Remover a constante STEPS
2. Remover o import do StepIndicator
3. Remover os dois blocos de JSX do StepIndicator (desktop e mobile)
4. Manter o hook useSteps pois ele ainda é usado para controlar o fluxo interno

RESULTADO ESPERADO:
- Tela de transcrição sem o subheader de steps
- Funcionalidade de transcrição continua funcionando normalmente

NÃO ALTERAR:
- Lógica de transcrição
- ProgressOverlay
- YouTubeInput e VideoPreview

COMO TESTAR:
1. Acessar /transcricao
2. Verificar que não há mais "1 Adicionar Vídeo | 2 Transcrevendo"
3. Colar URL do YouTube e transcrever - deve funcionar normalmente
```

---

# PROMPT 2: Remover ícone do título "Matérias sobre tema"

```
CONTEXTO DO PROJETO:
- Arquivo: src/pages/criar/variantes/TextoBaseTema.jsx (508 linhas)
- Tela de seleção de matérias por tema em alta

PROBLEMA:
O título "📰 Matérias sobre [tema]" tem um emoji de jornal que deve ser removido.

CÓDIGO ATUAL (linhas 445-447):
```jsx
<h2 className="text-lg font-bold text-dark-gray mb-4">
  📰 Matérias sobre "{selectedTema?.name}"
</h2>
```

TAREFA:
Remover o emoji 📰 do título, mantendo apenas o texto.

RESULTADO ESPERADO:
```jsx
<h2 className="text-lg font-bold text-dark-gray mb-4">
  Matérias sobre "{selectedTema?.name}"
</h2>
```

NÃO ALTERAR:
- Estilo CSS do título
- Lógica de seleção de matérias
- Outros componentes

COMO TESTAR:
1. Ir para /criar
2. Clicar em "Tema em Alta"
3. Selecionar um tema
4. Verificar que o título não tem mais o emoji 📰
```

---

# PROMPT 3: Adicionar botão "Ir direto ao editor"

```
CONTEXTO DO PROJETO:
- Arquivo: src/pages/criar/index.jsx (222 linhas)
- Tela de seleção do ponto de partida para criar matéria
- Context: useCriar() disponível com setFonte()

PROBLEMA:
Usuário quer opção de pular todas as etapas e ir direto ao editor sem selecionar fonte.

CÓDIGO ATUAL (linhas 196-203):
```jsx
{/* Dica */}
<div className="max-w-3xl mx-auto">
  <TipBox>
    Não importa qual fonte escolher, você poderá adicionar
    materiais complementares (links, PDFs, vídeos) na etapa 3
  </TipBox>
</div>
```

TAREFA:
Adicionar um botão secundário abaixo da TipBox que permite ir direto ao editor.

IMPLEMENTAÇÃO ESPERADA:
```jsx
{/* Dica */}
<div className="max-w-3xl mx-auto">
  <TipBox>
    Não importa qual fonte escolher, você poderá adicionar
    materiais complementares (links, PDFs, vídeos) na etapa 3
  </TipBox>

  {/* Botão para ir direto ao editor */}
  <div className="mt-6 text-center">
    <button
      onClick={() => {
        setFonte('manual', { skipSteps: true });
        navigate('/criar/editor');
      }}
      className="text-medium-gray hover:text-tmc-orange text-sm underline transition-colors"
    >
      Ou ir direto ao editor sem ponto de partida →
    </button>
  </div>
</div>
```

ALTERNATIVA (botão mais visível):
```jsx
<div className="mt-6 flex justify-center">
  <button
    onClick={() => {
      setFonte('manual', { skipSteps: true });
      navigate('/criar/editor');
    }}
    className="px-4 py-2 border border-light-gray text-medium-gray rounded-lg hover:border-tmc-orange hover:text-tmc-orange transition-colors text-sm"
  >
    Ir direto ao editor
  </button>
</div>
```

NÃO ALTERAR:
- Grid de cards de fonte
- Lógica dos seletores (tema, feed, etc.)
- Modais de URL

COMO TESTAR:
1. Acessar /criar
2. Ver novo botão "Ir direto ao editor" ou link
3. Clicar e verificar que vai para /criar/editor
4. Editor deve abrir vazio/limpo
```

---

# PROMPT 4: "Adicionar mais matérias" deve mostrar lista inline

```
CONTEXTO DO PROJETO:
- Arquivo: src/pages/criar/variantes/TextoBaseFeed.jsx (367 linhas)
- Tela de edição de matérias selecionadas do Feed
- Botão "Adicionar mais matérias" atualmente redireciona para /criar

PROBLEMA:
Quando clica em "Adicionar mais matérias", redireciona para a tela de ponto de partida.
Deveria mostrar uma lista inline com as matérias disponíveis para adicionar.

CÓDIGO ATUAL (linhas 246-253):
```jsx
{/* Botao adicionar mais */}
<button
  onClick={onChangeSource}
  className="w-full mt-4 p-3 border border-dashed border-light-gray rounded-lg text-medium-gray hover:border-tmc-orange hover:text-tmc-orange transition-colors flex items-center justify-center gap-2"
>
  <Plus size={16} />
  <span className="text-sm">Adicionar mais matérias</span>
</button>
```

ESTRUTURA DE DADOS DISPONÍVEL:
- fonte.dados: Array de artigos já selecionados
- Precisa buscar artigos disponíveis (do mockData ou API)

TAREFA:
1. Criar estado para controlar exibição do seletor inline
2. Quando clicar em "Adicionar mais", expandir seletor inline (não redirecionar)
3. Mostrar lista de matérias disponíveis (que ainda não foram selecionadas)
4. Permitir selecionar/deselecionar e confirmar adição
5. Atualizar fonte.dados com as novas matérias

IMPLEMENTAÇÃO ESPERADA:
```jsx
// Novo estado
const [showAddMore, setShowAddMore] = useState(false);
const [availableArticles, setAvailableArticles] = useState([]);
const [newSelections, setNewSelections] = useState(new Set());

// Carregar artigos disponíveis (excluindo já selecionados)
useEffect(() => {
  // Em produção, buscar da API
  // Por ora, usar mockData
  const alreadySelected = new Set(materias.map(m => m.id.replace('art-', '')));
  const available = mockArticles.filter(a => !alreadySelected.has(a.id));
  setAvailableArticles(available);
}, [materias]);

// Handler para adicionar mais
const handleAddMore = () => {
  setShowAddMore(true);
};

const handleConfirmAddMore = () => {
  const newArticles = availableArticles.filter(a => newSelections.has(a.id));
  // Notificar parent para atualizar fonte.dados
  // ou usar context diretamente
  setShowAddMore(false);
  setNewSelections(new Set());
};

// No JSX, substituir o botão por:
{showAddMore ? (
  <div className="mt-4 border border-light-gray rounded-lg p-4">
    <div className="flex items-center justify-between mb-3">
      <h4 className="font-medium text-dark-gray">Adicionar matérias</h4>
      <button
        onClick={() => setShowAddMore(false)}
        className="text-medium-gray hover:text-dark-gray"
      >
        <X size={16} />
      </button>
    </div>

    <div className="space-y-2 max-h-48 overflow-y-auto">
      {availableArticles.map(article => (
        <label
          key={article.id}
          className={`
            flex items-center gap-3 p-2 rounded-lg cursor-pointer
            ${newSelections.has(article.id) ? 'bg-orange-50' : 'hover:bg-off-white'}
          `}
        >
          <input
            type="checkbox"
            checked={newSelections.has(article.id)}
            onChange={() => {
              const newSet = new Set(newSelections);
              if (newSet.has(article.id)) {
                newSet.delete(article.id);
              } else {
                newSet.add(article.id);
              }
              setNewSelections(newSet);
            }}
            className="w-4 h-4 text-tmc-orange rounded"
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-dark-gray line-clamp-1">
              {article.title}
            </p>
            <p className="text-xs text-medium-gray">{article.source}</p>
          </div>
        </label>
      ))}
    </div>

    {availableArticles.length === 0 && (
      <p className="text-sm text-medium-gray text-center py-4">
        Não há mais matérias disponíveis
      </p>
    )}

    <button
      onClick={handleConfirmAddMore}
      disabled={newSelections.size === 0}
      className="w-full mt-3 py-2 bg-tmc-orange text-white rounded-lg disabled:opacity-50"
    >
      Adicionar {newSelections.size} matéria(s)
    </button>
  </div>
) : (
  <button
    onClick={handleAddMore}
    className="w-full mt-4 p-3 border border-dashed border-light-gray rounded-lg..."
  >
    <Plus size={16} />
    <span className="text-sm">Adicionar mais matérias</span>
  </button>
)}
```

IMPORT ADICIONAL:
```jsx
import { X } from 'lucide-react';
import { articles as mockArticles } from '../../../data/mockData';
```

NÃO ALTERAR:
- Lista de matérias já selecionadas
- Lógica de tópicos e edição
- ContentStats

COMO TESTAR:
1. Selecionar matérias na Redação e ir para TextoBase
2. Clicar em "Adicionar mais matérias"
3. Deve aparecer lista inline (não redirecionar)
4. Selecionar mais matérias e confirmar
5. Novas matérias devem aparecer na lista
```

---

# PROMPT 5: Fluxo de tema - ir para edição se selecionar matérias

```
CONTEXTO DO PROJETO:
- Arquivo: src/pages/criar/variantes/TextoBaseTema.jsx (508 linhas)
- Arquivo: src/pages/criar/TextoBasePage.jsx (controla navegação)
- Fluxo atual: Tema > Seleciona matérias > Vai para Configurar (errado)
- Fluxo esperado: Tema > Seleciona matérias > Vai para Edição (como Feed)

PROBLEMA:
Quando o usuário escolhe um tema E seleciona matérias daquele tema:
- ATUAL: Vai direto para Configurar
- ESPERADO: Vai para tela de edição (selecionar tópicos, como no fluxo Feed)

Se não selecionar nenhuma matéria, aí sim vai direto para Configurar.

CÓDIGO ATUAL DO TEXTOBPASETEMA (linhas 480-490):
```jsx
{/* Opcao de pular */}
{onSkipToConfig && (
  <div className="flex justify-center">
    <button
      onClick={onSkipToConfig}
      className="text-medium-gray hover:text-tmc-orange text-sm"
    >
      Pular seleção de matérias e ir direto para Configurações →
    </button>
  </div>
)}
```

LÓGICA ATUAL:
- TextoBaseTema sempre mostra botão de pular
- Não há botão "Continuar" que leve para edição de tópicos

TAREFA:
1. Adicionar botão "Continuar" que aparece quando há matérias selecionadas
2. "Continuar" deve transformar as matérias selecionadas em formato de tópicos
3. Navegar para uma view de edição (pode reutilizar TextoBaseFeed ou criar view híbrida)
4. Se não tiver matérias selecionadas, manter botão "Pular para Configurações"

IMPLEMENTAÇÃO ESPERADA:
```jsx
{/* Botões de ação */}
<div className="flex flex-col items-center gap-3 mt-6">
  {/* Continuar - aparece quando tem matérias selecionadas */}
  {selectedArticles.size > 0 && (
    <button
      onClick={() => {
        // Transformar matérias selecionadas em formato para edição
        const selectedMaterias = materias.filter(m => selectedArticles.has(m.id));
        onContinueWithArticles?.(selectedMaterias);
      }}
      className="px-6 py-3 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium"
    >
      Continuar com {selectedArticles.size} matéria(s) selecionada(s)
    </button>
  )}

  {/* Pular - sempre disponível */}
  {onSkipToConfig && (
    <button
      onClick={onSkipToConfig}
      className="text-medium-gray hover:text-tmc-orange text-sm"
    >
      {selectedArticles.size > 0
        ? 'Ou pular edição e ir direto para Configurações'
        : 'Pular seleção de matérias e ir direto para Configurações →'
      }
    </button>
  )}
</div>
```

NOVA PROP NECESSÁRIA:
```jsx
TextoBaseTema.propTypes = {
  fonte: PropTypes.object,
  onChangeSource: PropTypes.func,
  onDataChange: PropTypes.func,
  onSkipToConfig: PropTypes.func,
  onContinueWithArticles: PropTypes.func  // NOVA PROP
};
```

NO TEXTOBBASEPAGE.JSX - HANDLER:
```jsx
const handleContinueWithTemaArticles = (articles) => {
  // Converter artigos do tema para formato de matérias editáveis
  // Isso vai mudar o tipo de fonte para 'feed-like' e ir para edição
  setFonte('tema-articles', articles);
  // Ou mudar estado interno para mostrar view de edição
  setShowTopicEditor(true);
};
```

ALTERNATIVA MAIS SIMPLES:
Reutilizar TextoBaseFeed passando as matérias do tema:
```jsx
// Em TextoBasePage.jsx
if (fonte.tipo === 'tema' && fonte.dados?.selectedArticles?.length > 0) {
  // Mostrar TextoBaseFeed com as matérias do tema
  return <TextoBaseFeed fonte={{ tipo: 'tema', dados: fonte.dados.selectedArticles }} ... />;
}
```

NÃO ALTERAR:
- Seleção de tema (step 1)
- Visualização de matérias disponíveis
- Estilo dos cards de matéria

COMO TESTAR:
1. Ir para /criar > Tema em Alta
2. Selecionar um tema
3. Selecionar 2-3 matérias
4. Clicar em "Continuar com X matérias"
5. Deve ir para tela de edição de tópicos (como Feed)
6. Testar também sem selecionar matérias - deve ir direto para Configurar
```

---

# ORDEM DE IMPLEMENTAÇÃO RECOMENDADA

```
FÁCIL (30min cada):
1. Prompt 2: Remover ícone do título (1 linha de mudança)
2. Prompt 1: Remover subheader transcrição (remover código)

MÉDIO (1-2h cada):
3. Prompt 3: Botão "Ir direto ao editor" (adicionar componente)

COMPLEXO (2-4h cada):
4. Prompt 4: Lista inline de adicionar matérias (novo estado + UI)
5. Prompt 5: Fluxo tema com edição de matérias (lógica de navegação)
```

---

# DEPENDÊNCIAS ENTRE PROMPTS

```
Prompt 1 ─────> Independente
Prompt 2 ─────> Independente
Prompt 3 ─────> Independente
Prompt 4 ─────> Independente
Prompt 5 ─────> Pode reutilizar lógica similar ao Prompt 4
```

Todos os prompts são independentes e podem ser implementados em qualquer ordem.

---

**Documento gerado em:** 23/12/2025
**Próximo passo:** Executar prompts na ordem recomendada
