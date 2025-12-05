import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';

const UIContext = createContext(undefined);

export const useUI = () => {
  const context = useContext(UIContext);
  if (!context) {
    throw new Error('useUI must be used within UIProvider');
  }
  return context;
};

export const UIProvider = ({ children }) => {
  const [trendsSidebarOpen, setTrendsSidebarOpen] = useState(false);
  const [actionPanelOpen, setActionPanelOpen] = useState(false);

  const toggleTrendsSidebar = useCallback(() => {
    setTrendsSidebarOpen((prev) => !prev);
  }, []);

  const openTrendsSidebar = useCallback(() => {
    setTrendsSidebarOpen(true);
  }, []);

  const closeTrendsSidebar = useCallback(() => {
    setTrendsSidebarOpen(false);
  }, []);

  const toggleActionPanel = useCallback(() => {
    setActionPanelOpen((prev) => !prev);
  }, []);

  const openActionPanel = useCallback(() => {
    setActionPanelOpen(true);
  }, []);

  const closeActionPanel = useCallback(() => {
    setActionPanelOpen(false);
  }, []);

  const value = useMemo(
    () => ({
      trendsSidebarOpen,
      actionPanelOpen,
      toggleTrendsSidebar,
      openTrendsSidebar,
      closeTrendsSidebar,
      toggleActionPanel,
      openActionPanel,
      closeActionPanel,
    }),
    [
      trendsSidebarOpen,
      actionPanelOpen,
      toggleTrendsSidebar,
      openTrendsSidebar,
      closeTrendsSidebar,
      toggleActionPanel,
      openActionPanel,
      closeActionPanel,
    ]
  );

  return <UIContext.Provider value={value}>{children}</UIContext.Provider>;
};

UIProvider.propTypes = {
  children: PropTypes.node.isRequired,
};
