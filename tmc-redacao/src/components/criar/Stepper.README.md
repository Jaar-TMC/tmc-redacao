# Componente Stepper

Componente de navegação por etapas para o fluxo de criação de matéria da Ferramenta de Redação Jornalística TMC.

## Visão Geral

O `Stepper` é um componente reutilizável que exibe o progresso do usuário através das etapas do fluxo de criação de matéria. Ele oferece navegação visual clara e suporte completo para acessibilidade.

## Características

- ✅ **Responsivo**: Layout horizontal em desktop, vertical em mobile
- ✅ **Acessível**: Navegação por teclado, ARIA labels, focus indicators
- ✅ **Interativo**: Permite navegação para etapas anteriores
- ✅ **Visual**: Estados claros (completo, atual, pendente)
- ✅ **Animado**: Transições suaves de 300ms
- ✅ **Customizável**: Aceita qualquer número de etapas

## Instalação

O componente está localizado em:
```
src/components/criar/Stepper.jsx
```

## API

### Props

| Prop | Tipo | Obrigatório | Descrição |
|------|------|-------------|-----------|
| `steps` | `string[]` | Sim | Lista de nomes das etapas |
| `currentStep` | `number` | Sim | Índice da etapa atual (0-indexed) |
| `onStepClick` | `(stepIndex: number) => void` | Não | Callback quando uma etapa é clicada |

### Exemplo Básico

```jsx
import Stepper from '@/components/criar/Stepper';

function CriarMateriaFlow() {
  const [currentStep, setCurrentStep] = useState(0);

  return (
    <Stepper
      steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
      currentStep={currentStep}
      onStepClick={(stepIndex) => setCurrentStep(stepIndex)}
    />
  );
}
```

### Exemplo com React Router

```jsx
import { useNavigate, useLocation } from 'react-router-dom';
import Stepper from '@/components/criar/Stepper';

function CriarMateriaLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  const steps = ['Fonte', 'Texto-Base', 'Configurar', 'Editor'];
  const stepRoutes = [
    '/criar',
    '/criar/texto-base',
    '/criar/configurar',
    '/criar/editor'
  ];

  // Determina a etapa atual baseada na rota
  const currentStep = stepRoutes.findIndex(route =>
    location.pathname.startsWith(route)
  );

  return (
    <div>
      <Stepper
        steps={steps}
        currentStep={currentStep}
        onStepClick={(stepIndex) => navigate(stepRoutes[stepIndex])}
      />
      {/* Conteúdo da página */}
    </div>
  );
}
```

## Estados Visuais

### Desktop (≥768px)
```
     ●─────────────●─────────────○─────────────○
   Fonte       Texto-Base    Configurar     Editor
 (completo)   (completo)      (atual)     (pendente)
```

### Mobile (<768px)
```
● Fonte
│ Completo
│
● Texto-Base
│ Completo
│
● Configurar
│ Atual
│
○ Editor
  Pendente
```

## Comportamento

### Navegação

- **Etapas anteriores**: Clicáveis, permitem navegação para trás
- **Etapa atual**: Não clicável, exibe ring de destaque
- **Etapas futuras**: Não clicáveis, visual esmaecido

### Estados dos Círculos

| Estado | Visual | Cor de Fundo | Ícone |
|--------|--------|--------------|-------|
| **Completo** | Preenchido | `tmc-orange` (#E87722) | Círculo sólido |
| **Atual** | Preenchido + Ring | `tmc-orange` + ring 20% | Círculo sólido |
| **Pendente** | Vazio | `light-gray` (#E0E0E0) | Círculo outline |

### Estados das Linhas

| Estado | Cor |
|--------|-----|
| **Conecta etapas completas** | `tmc-orange` (#E87722) |
| **Conecta etapa pendente** | `light-gray` (#E0E0E0) |

## Acessibilidade

### Navegação por Teclado

| Tecla | Ação |
|-------|------|
| `Tab` | Navega entre etapas clicáveis |
| `Shift + Tab` | Navega para trás |
| `Enter` ou `Space` | Ativa a etapa focada |

### ARIA

- `role="navigation"` no container principal
- `aria-label="Progresso da criação de matéria"` no nav
- `aria-current="step"` na etapa atual
- `aria-label` descritivo em cada botão de etapa
- `aria-hidden="true"` em elementos decorativos
- `tabIndex={-1}` em etapas não clicáveis

### Leitores de Tela

Cada etapa anuncia:
- Nome da etapa
- Status: "Completo", "Atual" ou "Pendente"

Exemplo: "Fonte - Completo", "Texto-Base - Atual"

### Focus Indicators

- Outline laranja (`tmc-orange`) em elementos focados
- Offset de 2px para melhor visibilidade
- Hover scale em etapas clicáveis

## Responsividade

### Breakpoints

| Tamanho | Layout | Classes Tailwind |
|---------|--------|------------------|
| Desktop (≥768px) | Horizontal | `hidden md:block` |
| Mobile (<768px) | Vertical | `md:hidden` |

### Adaptações Mobile

1. **Layout vertical** com indicadores de conexão
2. **Labels de status** visíveis ("Completo", "Atual", "Pendente")
3. **Contador de progresso** abaixo do stepper
4. **Círculos menores** (8x8 vs 10x10 no desktop)

## Animações

Todas as transições usam:
```css
transition-all duration-300 ease-in-out
```

### Elementos Animados

- Mudança de cor dos círculos
- Mudança de cor das linhas
- Mudança de cor dos textos
- Scale em hover (1.05x)
- Ring appearance na etapa atual

### Reduced Motion

O componente respeita a preferência `prefers-reduced-motion` do usuário através dos estilos globais do projeto.

## Cores do Design System

```css
--color-tmc-orange: #E87722;   /* Etapas completas/atual */
--color-light-gray: #E0E0E0;   /* Etapas pendentes */
--color-medium-gray: #666666;  /* Texto secundário */
--color-success: #10B981;      /* Status "Completo" mobile */
```

## Estrutura HTML Semântica

```html
<nav aria-label="Progresso da criação de matéria">
  <ol>
    <li>
      <button aria-current="step" aria-label="Fonte - Completo">
        <div><!-- Círculo --></div>
        <span>Fonte</span>
        <span class="sr-only">Completo</span>
      </button>
      <div aria-hidden="true"><!-- Linha conectora --></div>
    </li>
    <!-- Mais etapas... -->
  </ol>
</nav>
```

## Casos de Uso

### 1. Fluxo Linear Simples
```jsx
// Usuário avança sequencialmente
<Stepper
  steps={steps}
  currentStep={currentStep}
  onStepClick={(i) => setCurrentStep(i)}
/>
```

### 2. Com Validação
```jsx
// Só permite avançar se validar
const handleStepClick = (stepIndex) => {
  if (stepIndex < currentStep) {
    // Permite voltar sempre
    navigate(routes[stepIndex]);
  }
};

<Stepper
  steps={steps}
  currentStep={currentStep}
  onStepClick={handleStepClick}
/>
```

### 3. Read-only
```jsx
// Apenas exibe progresso, sem navegação
<Stepper
  steps={steps}
  currentStep={currentStep}
  // Sem onStepClick
/>
```

## Testes

### Testes Manuais

- [ ] Navegação funciona em todas as direções
- [ ] Estados visuais corretos em cada etapa
- [ ] Responsivo (desktop → mobile → desktop)
- [ ] Navegação por teclado funciona
- [ ] Focus indicators visíveis
- [ ] Leitor de tela anuncia corretamente
- [ ] Transições suaves
- [ ] Hover states em etapas clicáveis

### Testes com Ferramentas

```bash
# Lighthouse Acessibilidade (deve ser 100)
npm run lighthouse

# axe DevTools
npm run test:a11y
```

## Performance

- **Bundle size**: ~2KB (minificado + gzip)
- **Renderizações**: Otimizado com React.memo (se necessário)
- **Animações**: CSS transitions (hardware-accelerated)

## Changelog

### v1.0.0 (2024-12-18)
- ✅ Implementação inicial
- ✅ Layout horizontal (desktop)
- ✅ Layout vertical (mobile)
- ✅ Navegação por clique
- ✅ Navegação por teclado
- ✅ ARIA labels completos
- ✅ Transições suaves
- ✅ Estados visuais claros
- ✅ Documentação completa

## Manutenção

### Adicionar Nova Etapa

Simplesmente adicione o nome ao array `steps`:

```jsx
// Antes
steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}

// Depois
steps={['Fonte', 'Texto-Base', 'Configurar', 'Revisão', 'Editor']}
```

### Customizar Cores

As cores são controladas por variáveis CSS no `index.css`. Para alterar, modifique:

```css
--color-tmc-orange: #SUA_COR;
--color-light-gray: #SUA_COR;
```

## Suporte

- **React**: ≥18.0.0
- **Tailwind CSS**: ≥3.0.0
- **Navegadores**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile**: iOS 14+, Android 10+

## Licença

Propriedade de TMC - Ferramenta de Redação Jornalística

## Autor

Desenvolvido para o projeto TMC - Ferramenta de Redação Jornalística
Baseado no planejamento UI/UX: `Planning/UI-UX-REWORK-CRIAR-MATERIA.md`
