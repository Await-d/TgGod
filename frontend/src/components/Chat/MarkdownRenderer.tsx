import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import './MarkdownRenderer.css';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  isOwn?: boolean;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className,
  isOwn = false
}) => {
  return (
    <div className={`markdown-renderer ${className || ''} ${isOwn ? 'own-message' : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // 自定义组件渲染
          p: ({ children }) => <p className="markdown-paragraph">{children}</p>,
          h1: ({ children }) => <h1 className="markdown-h1">{children}</h1>,
          h2: ({ children }) => <h2 className="markdown-h2">{children}</h2>,
          h3: ({ children }) => <h3 className="markdown-h3">{children}</h3>,
          h4: ({ children }) => <h4 className="markdown-h4">{children}</h4>,
          h5: ({ children }) => <h5 className="markdown-h5">{children}</h5>,
          h6: ({ children }) => <h6 className="markdown-h6">{children}</h6>,
          blockquote: ({ children }) => (
            <blockquote className="markdown-blockquote">{children}</blockquote>
          ),
          ul: ({ children }) => <ul className="markdown-ul">{children}</ul>,
          ol: ({ children }) => <ol className="markdown-ol">{children}</ol>,
          li: ({ children }) => <li className="markdown-li">{children}</li>,
          code: ({ node, inline, className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <div className="markdown-code-block">
                <div className="code-language">{match[1]}</div>
                <pre className="markdown-pre">
                  <code className={`language-${match[1]}`} {...props}>
                    {children}
                  </code>
                </pre>
              </div>
            ) : (
              <code className="markdown-inline-code" {...props}>
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="markdown-pre">{children}</pre>
          ),
          table: ({ children }) => (
            <div className="markdown-table-wrapper">
              <table className="markdown-table">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="markdown-thead">{children}</thead>,
          tbody: ({ children }) => <tbody className="markdown-tbody">{children}</tbody>,
          tr: ({ children }) => <tr className="markdown-tr">{children}</tr>,
          th: ({ children }) => <th className="markdown-th">{children}</th>,
          td: ({ children }) => <td className="markdown-td">{children}</td>,
          a: ({ href, children }) => (
            <a 
              href={href} 
              className="markdown-link"
              target="_blank" 
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              {children}
            </a>
          ),
          strong: ({ children }) => <strong className="markdown-strong">{children}</strong>,
          em: ({ children }) => <em className="markdown-em">{children}</em>,
          del: ({ children }) => <del className="markdown-del">{children}</del>,
          hr: () => <hr className="markdown-hr" />,
          input: ({ checked, ...props }: any) => (
            <input
              type="checkbox"
              checked={checked}
              className="markdown-checkbox"
              disabled
              {...props}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

// 检测内容是否包含 Markdown 格式
export const isMarkdownContent = (text: string): boolean => {
  const markdownPatterns = [
    /^#{1,6}\s+/m, // 标题
    /\*\*.*?\*\*/, // 粗体
    /\*.*?\*/, // 斜体
    /~~.*?~~/, // 删除线
    /`.*?`/, // 行内代码
    /```[\s\S]*?```/, // 代码块
    /^\s*[-*+]\s+/m, // 无序列表
    /^\s*\d+\.\s+/m, // 有序列表
    /^\s*>\s+/m, // 引用
    /\[.*?\]\(.*?\)/, // 链接
    /!\[.*?\]\(.*?\)/, // 图片
    /^\s*\|.*\|.*\|/m, // 表格
    /^\s*-{3,}$/m, // 分隔线
    /^\s*- \[[x ]\]/m, // 任务列表
  ];
  
  return markdownPatterns.some(pattern => pattern.test(text));
};

export default MarkdownRenderer;