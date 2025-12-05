import { useEffect } from 'react';

const useDocumentTitle = (title, retainOnUnmount = false) => {
  useEffect(() => {
    const previousTitle = document.title;

    if (title) {
      document.title = `${title} | TMC Redação`;
    } else {
      document.title = 'TMC Redação';
    }

    return () => {
      if (!retainOnUnmount) {
        document.title = previousTitle;
      }
    };
  }, [title, retainOnUnmount]);
};

export default useDocumentTitle;
