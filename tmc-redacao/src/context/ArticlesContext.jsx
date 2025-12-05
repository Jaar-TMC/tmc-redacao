import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';

const ArticlesContext = createContext(undefined);

export const useArticles = () => {
  const context = useContext(ArticlesContext);
  if (!context) {
    throw new Error('useArticles must be used within ArticlesProvider');
  }
  return context;
};

export const ArticlesProvider = ({ children }) => {
  const [selectedArticles, setSelectedArticles] = useState([]);

  const addArticle = useCallback((article) => {
    setSelectedArticles((prev) => {
      const isSelected = prev.some((a) => a.id === article.id);
      if (isSelected) {
        return prev.filter((a) => a.id !== article.id);
      }
      return [...prev, article];
    });
  }, []);

  const removeArticle = useCallback((articleId) => {
    setSelectedArticles((prev) => prev.filter((a) => a.id !== articleId));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedArticles([]);
  }, []);

  const isArticleSelected = useCallback((articleId) => {
    return selectedArticles.some((a) => a.id === articleId);
  }, [selectedArticles]);

  const value = useMemo(
    () => ({
      selectedArticles,
      addArticle,
      removeArticle,
      clearSelection,
      isArticleSelected,
    }),
    [selectedArticles, addArticle, removeArticle, clearSelection, isArticleSelected]
  );

  return (
    <ArticlesContext.Provider value={value}>
      {children}
    </ArticlesContext.Provider>
  );
};

ArticlesProvider.propTypes = {
  children: PropTypes.node.isRequired,
};
