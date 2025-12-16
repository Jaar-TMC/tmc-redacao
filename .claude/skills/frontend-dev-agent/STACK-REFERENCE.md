# Stack Reference - TMC Redação

Documentação de referência das tecnologias utilizadas no projeto.

---

## React 19

### Novidades do React 19

O projeto usa React 19.2.0, que inclui:

**1. Automatic Batching Melhorado**
```jsx
// React 19 agrupa automaticamente múltiplas atualizações
function handleClick() {
  setCount(c => c + 1);  // Não re-renderiza
  setFlag(f => !f);       // Não re-renderiza
  // Re-renderiza apenas uma vez no final
}
```

**2. Actions (novo)**
```jsx
// useTransition para ações assíncronas
const [isPending, startTransition] = useTransition();

function handleSubmit() {
  startTransition(async () => {
    await saveData();
  });
}

// isPending = true durante a execução
```

**3. useOptimistic (novo)**
```jsx
const [optimisticItems, addOptimistic] = useOptimistic(
  items,
  (currentItems, newItem) => [...currentItems, newItem]
);

// Atualização otimista antes da resposta do servidor
```

**4. use() Hook (novo)**
```jsx
// Pode usar promessas e contextos diretamente
function Component({ dataPromise }) {
  const data = use(dataPromise); // Suspende até resolver
  return <div>{data.title}</div>;
}
```

### Hooks Principais

```jsx
// Estado
const [state, setState] = useState(initialValue);

// Efeitos
useEffect(() => {
  // Executado após render
  return () => {
    // Cleanup
  };
}, [dependencies]);

// Contexto
const value = useContext(MyContext);

// Referências
const ref = useRef(initialValue);

// Callbacks memorizados
const memoizedCallback = useCallback(() => {
  doSomething(a, b);
}, [a, b]);

// Valores memorizados
const memoizedValue = useMemo(() => {
  return computeExpensiveValue(a, b);
}, [a, b]);

// Reducer para estado complexo
const [state, dispatch] = useReducer(reducer, initialState);
```

### Padrões de Componentes

```jsx
// Componente funcional padrão
function MyComponent({ prop1, prop2 }) {
  return <div>{prop1}</div>;
}

// Com children
function Container({ children }) {
  return <div className="container">{children}</div>;
}

// Componente controlado
function ControlledInput({ value, onChange }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

// Render props
function DataProvider({ children, data }) {
  return children(data);
}

// Compound components
function Tabs({ children }) {
  const [activeTab, setActiveTab] = useState(0);
  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      {children}
    </TabsContext.Provider>
  );
}
Tabs.Tab = TabItem;
Tabs.Panel = TabPanel;
```

---

## React Router 7

### Configuração de Rotas

```jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Rota simples */}
        <Route path="/" element={<HomePage />} />

        {/* Rota com parâmetro */}
        <Route path="/artigo/:id" element={<ArtigoPage />} />

        {/* Rotas aninhadas */}
        <Route path="/configuracoes" element={<ConfigLayout />}>
          <Route index element={<ConfigIndex />} />
          <Route path="perfil" element={<PerfilPage />} />
          <Route path="preferencias" element={<PreferenciasPage />} />
        </Route>

        {/* Redirect */}
        <Route path="/old" element={<Navigate to="/new" replace />} />

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### Lazy Loading

```jsx
import { lazy, Suspense } from 'react';

// Importação lazy
const TranscricaoPage = lazy(() => import('./pages/transcricao/TranscricaoPage'));

// Na rota
<Route
  path="/transcricao"
  element={
    <Suspense fallback={<PageLoadingFallback />}>
      <TranscricaoPage />
    </Suspense>
  }
/>
```

### Hooks de Navegação

```jsx
import {
  useNavigate,
  useParams,
  useSearchParams,
  useLocation,
  Link,
  NavLink
} from 'react-router-dom';

function MyComponent() {
  // Navegação programática
  const navigate = useNavigate();
  navigate('/destino');
  navigate(-1); // Voltar
  navigate('/destino', { replace: true }); // Sem histórico

  // Parâmetros da URL
  const { id } = useParams(); // /artigo/:id

  // Query strings
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q');
  setSearchParams({ q: 'novo valor' });

  // Localização atual
  const location = useLocation();
  // location.pathname, location.search, location.state

  return (
    <>
      {/* Link simples */}
      <Link to="/destino">Ir</Link>

      {/* NavLink com estado ativo */}
      <NavLink
        to="/pagina"
        className={({ isActive }) =>
          isActive ? 'text-blue-600' : 'text-gray-600'
        }
      >
        Página
      </NavLink>
    </>
  );
}
```

### Outlet para Rotas Aninhadas

```jsx
import { Outlet } from 'react-router-dom';

function ConfigLayout() {
  return (
    <div className="flex">
      <Sidebar />
      <main>
        {/* Renderiza a rota filha aqui */}
        <Outlet />
      </main>
    </div>
  );
}
```

---

## Tailwind CSS 4

### Configuração (index.css)

```css
@import "tailwindcss";

@theme {
  /* Cores customizadas */
  --color-primary-500: #E87722;
  --color-primary-600: #D66A1E;

  /* Fontes */
  --font-family-sans: 'Inter', system-ui, sans-serif;

  /* Espaçamentos customizados */
  --spacing-18: 4.5rem;
}
```

### Classes Utilitárias Essenciais

**Layout:**
```html
<!-- Flexbox -->
<div class="flex items-center justify-between gap-4">
<div class="flex flex-col items-start">
<div class="flex-1"> <!-- Cresce para preencher -->
<div class="flex-shrink-0"> <!-- Não encolhe -->

<!-- Grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
<div class="col-span-2"> <!-- Ocupa 2 colunas -->

<!-- Container -->
<div class="container mx-auto px-4">
<div class="max-w-7xl mx-auto">
```

**Espaçamento:**
```html
<!-- Padding -->
<div class="p-4">      <!-- 1rem todos os lados -->
<div class="px-4 py-2"> <!-- horizontal e vertical -->
<div class="pt-4 pb-2"> <!-- top e bottom -->

<!-- Margin -->
<div class="m-4">
<div class="mx-auto">   <!-- Centraliza horizontalmente -->
<div class="mt-4 mb-2">
<div class="-mt-2">     <!-- Margem negativa -->

<!-- Gap (em flex/grid) -->
<div class="gap-4">
<div class="gap-x-4 gap-y-2">
```

**Tipografia:**
```html
<!-- Tamanhos -->
<p class="text-xs">    <!-- 0.75rem -->
<p class="text-sm">    <!-- 0.875rem -->
<p class="text-base">  <!-- 1rem -->
<p class="text-lg">    <!-- 1.125rem -->
<p class="text-xl">    <!-- 1.25rem -->
<p class="text-2xl">   <!-- 1.5rem -->

<!-- Peso -->
<p class="font-normal">
<p class="font-medium">
<p class="font-semibold">
<p class="font-bold">

<!-- Cor -->
<p class="text-gray-900">  <!-- Escuro -->
<p class="text-gray-600">  <!-- Médio -->
<p class="text-gray-400">  <!-- Claro -->

<!-- Alinhamento -->
<p class="text-left text-center text-right">

<!-- Truncate -->
<p class="truncate">           <!-- Uma linha com ... -->
<p class="line-clamp-2">       <!-- Duas linhas com ... -->
```

**Cores:**
```html
<!-- Background -->
<div class="bg-white">
<div class="bg-gray-50">
<div class="bg-primary-500">
<div class="bg-blue-50">      <!-- Selecionado -->

<!-- Texto -->
<p class="text-gray-900">
<p class="text-primary-500">
<p class="text-red-500">      <!-- Erro -->
<p class="text-green-500">    <!-- Sucesso -->

<!-- Borda -->
<div class="border border-gray-200">
<div class="border-2 border-primary-500"> <!-- Selecionado -->
<div class="border-red-500">              <!-- Erro -->
```

**Bordas e Sombras:**
```html
<!-- Border radius -->
<div class="rounded">      <!-- 0.25rem -->
<div class="rounded-lg">   <!-- 0.5rem -->
<div class="rounded-full"> <!-- Circular -->

<!-- Sombras -->
<div class="shadow-sm">
<div class="shadow">
<div class="shadow-md">
<div class="shadow-lg">

<!-- Borda -->
<div class="border">
<div class="border-2">
<div class="border-t border-b"> <!-- Apenas top e bottom -->
```

**Responsividade:**
```html
<!-- Breakpoints: sm(640px), md(768px), lg(1024px), xl(1280px), 2xl(1536px) -->
<div class="w-full md:w-1/2 lg:w-1/3">
<div class="hidden md:block">         <!-- Esconde em mobile -->
<div class="md:hidden">               <!-- Mostra só em mobile -->
<div class="flex flex-col md:flex-row">
<div class="text-sm md:text-base">
```

**Estados:**
```html
<!-- Hover -->
<button class="bg-primary-500 hover:bg-primary-600">
<div class="hover:shadow-md">

<!-- Focus -->
<input class="focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
<button class="focus:outline-none focus:ring-2">

<!-- Active -->
<button class="active:bg-primary-700">

<!-- Disabled -->
<button class="disabled:opacity-50 disabled:cursor-not-allowed">

<!-- Group hover -->
<div class="group">
  <span class="group-hover:text-primary-500">
</div>
```

**Transições:**
```html
<div class="transition-all duration-200">
<div class="transition-colors duration-150">
<div class="transition-transform hover:scale-105">
```

**Posicionamento:**
```html
<!-- Position -->
<div class="relative">
<div class="absolute top-0 right-0">
<div class="fixed bottom-4 right-4">
<div class="sticky top-0">

<!-- Z-index -->
<div class="z-10">
<div class="z-50">

<!-- Inset -->
<div class="inset-0">          <!-- top/right/bottom/left: 0 -->
<div class="inset-x-0">        <!-- left/right: 0 -->
```

---

## Lucide React

### Importação e Uso

```jsx
import { Search, X, ChevronDown, Play, Check } from 'lucide-react';

// Uso básico
<Search className="w-5 h-5" />

// Com cor
<Search className="w-5 h-5 text-gray-400" />

// Acessibilidade (decorativo)
<Search className="w-5 h-5" aria-hidden="true" />

// Acessibilidade (informativo)
<Search className="w-5 h-5" aria-label="Buscar" role="img" />

// Tamanhos comuns
<Icon className="w-4 h-4" />  // Pequeno (16px)
<Icon className="w-5 h-5" />  // Médio (20px)
<Icon className="w-6 h-6" />  // Grande (24px)
<Icon className="w-8 h-8" />  // Extra grande (32px)
```

### Ícones Comuns no Projeto

```jsx
// Navegação
import { ArrowLeft, ArrowRight, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Menu, X } from 'lucide-react';

// Ações
import { Plus, Minus, Trash2, Edit, Edit2, Copy, ExternalLink, Download, Upload, Save, Send } from 'lucide-react';

// Status/Feedback
import { Check, CheckCircle, AlertCircle, AlertTriangle, Info, XCircle, Loader2 } from 'lucide-react';

// Mídia
import { Play, Pause, Square, Volume2, VolumeX, Video, Youtube, Mic } from 'lucide-react';

// Arquivos
import { File, FileText, Folder, Image, Film } from 'lucide-react';

// Interface
import { Search, Filter, Settings, Bell, User, Clock, Calendar, Eye, EyeOff } from 'lucide-react';

// Social/Branding
import { Youtube, Twitter, Globe, Link2 } from 'lucide-react';
```

### Spinner Animado

```jsx
import { Loader2 } from 'lucide-react';

// Spinner com animação
<Loader2 className="w-5 h-5 animate-spin" />

// Em botão de loading
<button disabled={isLoading}>
  {isLoading ? (
    <Loader2 className="w-4 h-4 animate-spin mr-2" />
  ) : (
    <Save className="w-4 h-4 mr-2" />
  )}
  Salvar
</button>
```

---

## PropTypes

### Tipos Básicos

```jsx
import PropTypes from 'prop-types';

Component.propTypes = {
  // Primitivos
  string: PropTypes.string,
  number: PropTypes.number,
  bool: PropTypes.bool,
  func: PropTypes.func,
  array: PropTypes.array,
  object: PropTypes.object,
  symbol: PropTypes.symbol,

  // Qualquer coisa renderizável
  node: PropTypes.node,

  // Elemento React
  element: PropTypes.element,

  // Instância de classe
  instance: PropTypes.instanceOf(MyClass),

  // Enum
  status: PropTypes.oneOf(['draft', 'published', 'archived']),

  // Union de tipos
  value: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number
  ]),

  // Array de tipo específico
  items: PropTypes.arrayOf(PropTypes.string),

  // Objeto com propriedades específicas
  user: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    email: PropTypes.string
  }),

  // Objeto com valores de tipo específico
  scores: PropTypes.objectOf(PropTypes.number),

  // Qualquer tipo (evitar)
  anything: PropTypes.any,

  // Obrigatório
  required: PropTypes.string.isRequired,

  // Children
  children: PropTypes.node
};

// Valores padrão
Component.defaultProps = {
  status: 'draft',
  items: []
};
```

### Padrão do Projeto

```jsx
import PropTypes from 'prop-types';

function ArticleCard({ article, isSelected, onSelect, onView }) {
  // ... implementação
}

ArticleCard.propTypes = {
  article: PropTypes.shape({
    id: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    source: PropTypes.string.isRequired,
    category: PropTypes.string,
    publishedAt: PropTypes.string.isRequired,
    preview: PropTypes.string
  }).isRequired,
  isSelected: PropTypes.bool,
  onSelect: PropTypes.func.isRequired,
  onView: PropTypes.func
};

ArticleCard.defaultProps = {
  isSelected: false,
  onView: null
};

export default ArticleCard;
```

---

## Vite

### Scripts Disponíveis

```bash
npm run dev      # Inicia servidor de desenvolvimento
npm run build    # Build de produção
npm run preview  # Preview do build
npm run lint     # Executa ESLint
```

### Importações Especiais

```jsx
// Assets (imagens, SVGs)
import logo from './assets/logo.svg';
<img src={logo} alt="Logo" />

// CSS Modules (se configurado)
import styles from './Component.module.css';
<div className={styles.container}>

// JSON
import data from './data.json';

// Raw text
import readme from './README.md?raw';

// URL de asset
import workletURL from './worker.js?url';
```

### Variáveis de Ambiente

```jsx
// Prefixo VITE_ para expor ao cliente
// .env
VITE_API_URL=https://api.example.com

// Uso
const apiUrl = import.meta.env.VITE_API_URL;

// Variáveis built-in
import.meta.env.MODE      // 'development' ou 'production'
import.meta.env.DEV       // true em dev
import.meta.env.PROD      // true em prod
import.meta.env.BASE_URL  // Base URL da aplicação
```

---

## Context API

### Criando um Context

```jsx
// src/context/MyContext.jsx
import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';

const MyContext = createContext(null);

export function MyProvider({ children }) {
  const [state, setState] = useState(initialValue);

  const updateState = useCallback((newValue) => {
    setState(prev => ({ ...prev, ...newValue }));
  }, []);

  const resetState = useCallback(() => {
    setState(initialValue);
  }, []);

  // Memorizar o valor para evitar re-renders desnecessários
  const value = useMemo(() => ({
    state,
    updateState,
    resetState
  }), [state, updateState, resetState]);

  return (
    <MyContext.Provider value={value}>
      {children}
    </MyContext.Provider>
  );
}

MyProvider.propTypes = {
  children: PropTypes.node.isRequired
};

// Hook customizado para usar o context
export function useMyContext() {
  const context = useContext(MyContext);
  if (!context) {
    throw new Error('useMyContext deve ser usado dentro de MyProvider');
  }
  return context;
}
```

### Usando o Context

```jsx
// Em App.jsx ou main.jsx
import { MyProvider } from './context/MyContext';

function App() {
  return (
    <MyProvider>
      <Router>
        {/* ... */}
      </Router>
    </MyProvider>
  );
}

// Em qualquer componente
import { useMyContext } from '../context/MyContext';

function MyComponent() {
  const { state, updateState } = useMyContext();

  return (
    <button onClick={() => updateState({ key: 'value' })}>
      {state.key}
    </button>
  );
}
```

### Combinando Múltiplos Contexts

```jsx
// src/context/index.js
export { ArticlesProvider, useArticles } from './ArticlesContext';
export { FiltersProvider, useFilters } from './FiltersContext';
export { UIProvider, useUI } from './UIContext';

// Em App.jsx
import { ArticlesProvider, FiltersProvider, UIProvider } from './context';

function App() {
  return (
    <UIProvider>
      <FiltersProvider>
        <ArticlesProvider>
          <Router>{/* ... */}</Router>
        </ArticlesProvider>
      </FiltersProvider>
    </UIProvider>
  );
}
```
