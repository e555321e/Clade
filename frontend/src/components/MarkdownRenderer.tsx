import ReactMarkdown from 'react-markdown';
import type { CSSProperties } from 'react';

interface Props {
  content: string;
  className?: string;
  style?: CSSProperties;
}

/**
 * Markdown 渲染组件
 * 用于将 markdown 格式的文本渲染为格式化的 HTML
 */
export function MarkdownRenderer({ content, className, style }: Props) {
  const baseStyle: CSSProperties = {
    lineHeight: '1.8',
    color: 'rgba(255, 255, 255, 0.9)',
    wordWrap: 'break-word',
    overflowWrap: 'break-word',
    whiteSpace: 'pre-wrap',
    maxWidth: '100%',
    ...style
  };

  return (
    <div className={className} style={baseStyle}>
      <ReactMarkdown
        components={{
          // 标题样式 - 使用更柔和的颜色
          h1: ({ children }) => (
            <h1 style={{ 
              fontSize: '1.4rem', 
              fontWeight: 600, 
              color: 'rgba(255, 255, 255, 0.95)',
              marginTop: '1.2rem',
              marginBottom: '0.6rem',
              borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
              paddingBottom: '0.4rem',
              wordWrap: 'break-word'
            }}>
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 style={{ 
              fontSize: '1.2rem', 
              fontWeight: 600, 
              color: 'rgba(255, 255, 255, 0.9)',
              marginTop: '1rem',
              marginBottom: '0.5rem',
              wordWrap: 'break-word'
            }}>
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 style={{ 
              fontSize: '1.05rem', 
              fontWeight: 600, 
              color: 'rgba(255, 255, 255, 0.85)',
              marginTop: '0.8rem',
              marginBottom: '0.4rem',
              wordWrap: 'break-word'
            }}>
              {children}
            </h3>
          ),
          // 段落样式
          p: ({ children }) => (
            <p style={{ 
              margin: '0.6rem 0',
              lineHeight: '1.75',
              wordWrap: 'break-word',
              overflowWrap: 'break-word'
            }}>
              {children}
            </p>
          ),
          // 列表样式
          ul: ({ children }) => (
            <ul style={{ 
              margin: '0.5rem 0',
              paddingLeft: '1.5rem',
              listStyleType: 'disc'
            }}>
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol style={{ 
              margin: '0.5rem 0',
              paddingLeft: '1.5rem'
            }}>
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li style={{ 
              margin: '0.25rem 0',
              lineHeight: '1.6',
              wordWrap: 'break-word'
            }}>
              {children}
            </li>
          ),
          // 强调样式 - 更柔和的颜色
          strong: ({ children }) => (
            <strong style={{ 
              fontWeight: 600, 
              color: 'rgba(255, 255, 255, 1)'
            }}>
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em style={{ 
              fontStyle: 'italic', 
              color: 'rgba(255, 255, 255, 0.8)'
            }}>
              {children}
            </em>
          ),
          // 代码块样式
          code: ({ children }) => (
            <code style={{ 
              background: 'rgba(0, 0, 0, 0.3)',
              padding: '0.15rem 0.4rem',
              borderRadius: '4px',
              fontSize: '0.9em',
              fontFamily: 'monospace',
              color: 'rgba(129, 230, 217, 0.9)',
              wordWrap: 'break-word'
            }}>
              {children}
            </code>
          ),
          // 引用块样式
          blockquote: ({ children }) => (
            <blockquote style={{ 
              borderLeft: '3px solid rgba(99, 179, 237, 0.6)',
              paddingLeft: '1rem',
              margin: '0.8rem 0',
              fontStyle: 'italic',
              color: 'rgba(255, 255, 255, 0.7)'
            }}>
              {children}
            </blockquote>
          ),
          // 分割线样式
          hr: () => (
            <hr style={{ 
              border: 'none',
              borderTop: '1px solid rgba(255, 255, 255, 0.1)',
              margin: '1rem 0'
            }} />
          ),
          // 链接样式
          a: ({ href, children }) => (
            <a 
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{ 
                color: 'rgba(129, 199, 245, 0.9)',
                textDecoration: 'underline'
              }}
            >
              {children}
            </a>
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

/**
 * 紧凑版 Markdown 渲染组件
 * 适用于列表项等空间受限的场景
 */
export function MarkdownCompact({ content, style }: Omit<Props, 'className'>) {
  const compactStyle: CSSProperties = {
    lineHeight: '1.6',
    color: 'rgba(255, 255, 255, 0.85)',
    wordWrap: 'break-word',
    overflowWrap: 'break-word',
    ...style
  };

  return (
    <div style={compactStyle}>
      <ReactMarkdown
        components={{
          p: ({ children }) => <span style={{ wordWrap: 'break-word' }}>{children}</span>,
          strong: ({ children }) => (
            <strong style={{ fontWeight: 600, color: 'rgba(255, 255, 255, 1)' }}>{children}</strong>
          ),
          em: ({ children }) => (
            <em style={{ fontStyle: 'italic' }}>{children}</em>
          ),
          code: ({ children }) => (
            <code style={{ 
              background: 'rgba(0, 0, 0, 0.3)',
              padding: '0.1rem 0.3rem',
              borderRadius: '3px',
              fontSize: '0.85em',
              color: 'rgba(129, 230, 217, 0.9)'
            }}>
              {children}
            </code>
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
