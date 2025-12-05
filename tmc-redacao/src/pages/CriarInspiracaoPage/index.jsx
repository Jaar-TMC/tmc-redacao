import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import StepOne from './StepOne';
import StepTwo from './StepTwo';
import StepThree from './StepThree';

/**
 * CriarInspiracaoPage - Main orchestrator component for creating content with AI inspiration
 * Manages the three-step workflow:
 * 1. Article selection and configuration
 * 2. Content generation (loading)
 * 3. Result review and editing
 */
const CriarInspiracaoPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState(1);
  const [articles, setArticles] = useState([]);
  const [expandedArticle, setExpandedArticle] = useState(null);
  const [selectedParagraphs, setSelectedParagraphs] = useState({});
  const [selectedTone, setSelectedTone] = useState(null);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [generatedContent, setGeneratedContent] = useState(null);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingText, setLoadingText] = useState('');

  // Initialize articles from navigation state
  useEffect(() => {
    if (location.state?.articles) {
      setArticles(location.state.articles);
      // Initialize all paragraphs as selected
      const initialSelection = {};
      location.state.articles.forEach((article) => {
        initialSelection[article.id] = article.content.split('. ').map((_, i) => i);
      });
      setSelectedParagraphs(initialSelection);
    }
  }, [location.state]);

  /**
   * Toggle paragraph selection
   * @param {string|number} articleId - Article ID
   * @param {number} paragraphIndex - Paragraph index
   */
  const handleToggleParagraph = useCallback((articleId, paragraphIndex) => {
    setSelectedParagraphs((prev) => {
      const current = prev[articleId] || [];
      if (current.includes(paragraphIndex)) {
        return { ...prev, [articleId]: current.filter((i) => i !== paragraphIndex) };
      }
      return { ...prev, [articleId]: [...current, paragraphIndex] };
    });
  }, []);

  /**
   * Handle content generation with simulated loading
   */
  const handleGenerate = useCallback(() => {
    setStep(2);
    setLoadingProgress(0);
    const loadingTexts = [
      'Analisando as matérias selecionadas...',
      'Aplicando o tom e a persona escolhidos...',
      'Gerando conteúdo original e exclusivo...',
      'Otimizando para SEO e legibilidade...'
    ];

    let progress = 0;
    let textIndex = 0;

    const interval = setInterval(() => {
      progress += 2;
      setLoadingProgress(progress);

      if (progress % 25 === 0 && textIndex < loadingTexts.length) {
        setLoadingText(loadingTexts[textIndex]);
        textIndex++;
      }

      if (progress >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          setGeneratedContent({
            title: 'Nova análise: Impactos econômicos das medidas governamentais',
            content: `O cenário econômico brasileiro passa por um momento de transformação significativa. As recentes medidas anunciadas pelo governo federal têm gerado debates acalorados entre especialistas e investidores.

Segundo análises de mercado, as políticas de incentivo fiscal podem impulsionar o crescimento do PIB em até 2% nos próximos trimestres. "Estamos diante de uma oportunidade única de reposicionamento econômico", afirma um dos principais economistas do país.

O setor industrial, particularmente afetado nos últimos anos, deve ser um dos maiores beneficiados. Com a redução de impostos prevista, empresas poderão reinvestir recursos em modernização e expansão de suas operações.

Entretanto, críticos apontam para possíveis riscos fiscais no médio prazo. A sustentabilidade das medidas dependerá de um ajuste fino nas contas públicas e do comportamento da inflação nos próximos meses.`,
            wordCount: 156,
            readTime: '2 min',
            originalityScore: 87,
            seoScore: 72
          });
          setStep(3);
        }, 500);
      }
    }, 50);
  }, []);

  /**
   * Navigate to editor with generated content
   */
  const handleUseDraft = useCallback(() => {
    navigate('/criar', { state: { draft: generatedContent } });
  }, [navigate, generatedContent]);

  /**
   * Navigate back to home
   */
  const handleCancel = useCallback(() => {
    navigate('/');
  }, [navigate]);

  /**
   * Reset to step one
   */
  const handleReset = useCallback(() => {
    setStep(1);
  }, []);

  // Render appropriate step component
  if (step === 1) {
    return (
      <StepOne
        articles={articles}
        expandedArticle={expandedArticle}
        onExpandArticle={setExpandedArticle}
        selectedParagraphs={selectedParagraphs}
        onToggleParagraph={handleToggleParagraph}
        selectedTone={selectedTone}
        onSelectTone={setSelectedTone}
        selectedPersona={selectedPersona}
        onSelectPersona={setSelectedPersona}
        onCancel={handleCancel}
        onGenerate={handleGenerate}
      />
    );
  }

  if (step === 2) {
    return (
      <StepTwo
        loadingProgress={loadingProgress}
        loadingText={loadingText}
      />
    );
  }

  return (
    <StepThree
      generatedContent={generatedContent}
      articles={articles}
      onRegenerate={handleGenerate}
      onUseDraft={handleUseDraft}
      onReset={handleReset}
    />
  );
};

export default CriarInspiracaoPage;
