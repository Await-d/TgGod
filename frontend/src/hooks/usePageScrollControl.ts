import { useEffect } from 'react';

export interface PageScrollControlOptions {
  disableBodyScroll?: boolean;
  disableRootScroll?: boolean;
  restoreOnUnmount?: boolean;
}

/**
 * 页面滚动控制 Hook
 * 用于精确控制不同页面的滚动行为
 */
export const usePageScrollControl = (options: PageScrollControlOptions = {}) => {
  const {
    disableBodyScroll = false,
    disableRootScroll = false,
    restoreOnUnmount = true
  } = options;

  useEffect(() => {
    const body = document.body;
    const html = document.documentElement;
    const root = document.getElementById('root');

    // 保存原始样式
    const originalBodyStyles = {
      overflow: body.style.overflow,
      height: body.style.height,
    };
    
    const originalHtmlStyles = {
      overflow: html.style.overflow,
      height: html.style.height,
    };

    const originalRootStyles = root ? {
      overflow: root.style.overflow,
      height: root.style.height,
    } : null;

    // 应用滚动控制
    if (disableBodyScroll) {
      body.classList.add('chat-page-active');
      html.classList.add('chat-page-active');
      
      body.style.overflow = 'hidden';
      body.style.height = '100%';
      html.style.overflow = 'hidden';
      html.style.height = '100%';
    }

    if (disableRootScroll && root) {
      root.style.overflow = 'hidden';
      root.style.height = '100%';
    }

    // 清理函数
    return () => {
      if (restoreOnUnmount) {
        // 恢复原始样式
        body.classList.remove('chat-page-active');
        html.classList.remove('chat-page-active');

        body.style.overflow = originalBodyStyles.overflow;
        body.style.height = originalBodyStyles.height;
        html.style.overflow = originalHtmlStyles.overflow;
        html.style.height = originalHtmlStyles.height;

        if (root && originalRootStyles) {
          root.style.overflow = originalRootStyles.overflow;
          root.style.height = originalRootStyles.height;
        }
      }
    };
  }, [disableBodyScroll, disableRootScroll, restoreOnUnmount]);

  // 提供手动控制函数
  const enableScroll = () => {
    const body = document.body;
    const html = document.documentElement;
    const root = document.getElementById('root');

    body.classList.remove('chat-page-active');
    html.classList.remove('chat-page-active');

    body.style.overflow = 'auto';
    html.style.overflow = 'auto';
    
    if (root) {
      root.style.overflow = 'auto';
    }
  };

  const disableScroll = () => {
    const body = document.body;
    const html = document.documentElement;
    const root = document.getElementById('root');

    body.classList.add('chat-page-active');
    html.classList.add('chat-page-active');

    body.style.overflow = 'hidden';
    html.style.overflow = 'hidden';
    
    if (root) {
      root.style.overflow = 'hidden';
    }
  };

  return {
    enableScroll,
    disableScroll
  };
};

/**
 * 聊天页面专用的滚动控制 Hook
 */
export const useChatPageScrollControl = () => {
  return usePageScrollControl({
    disableBodyScroll: true,
    disableRootScroll: true,
    restoreOnUnmount: true
  });
};

/**
 * 普通页面的滚动控制 Hook（恢复正常滚动）
 */
export const useNormalPageScrollControl = () => {
  return usePageScrollControl({
    disableBodyScroll: false,
    disableRootScroll: false,
    restoreOnUnmount: false
  });
};