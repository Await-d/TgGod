/**
 * PageContainer Component
 * 统一的页面容器组件，提供一致的页面布局和功能
 */

import React from 'react';
import { Breadcrumb, Spin, Alert, Skeleton } from 'antd';
import { Link } from 'react-router-dom';
import { HomeOutlined } from '@ant-design/icons';
import { useIsMobile } from '../../hooks/useMobileGestures';
import './PageContainer.css';

export interface BreadcrumbItem {
  title: string;
  path?: string;
  icon?: React.ReactNode;
}

export interface PageContainerProps {
  /** 页面标题 */
  title: string;
  /** 页面描述 */
  description?: string;
  /** 面包屑导航 */
  breadcrumb?: BreadcrumbItem[];
  /** 右侧操作区 */
  extra?: React.ReactNode;
  /** 加载状态 */
  loading?: boolean;
  /** 错误信息 */
  error?: string | null;
  /** 页面内容 */
  children: React.ReactNode;
  /** 自定义类名 */
  className?: string;
  /** 是否全宽 */
  fullWidth?: boolean;
  /** 是否无内边距 */
  noPadding?: boolean;
  /** 是否显示骨架屏 */
  skeleton?: boolean;
  /** 标题下方的标签或额外信息 */
  tags?: React.ReactNode;
  /** 页脚内容 */
  footer?: React.ReactNode;
  /** 错误重试回调 */
  onRetry?: () => void;
}

const PageContainer: React.FC<PageContainerProps> = ({
  title,
  description,
  breadcrumb,
  extra,
  loading = false,
  error = null,
  children,
  className = '',
  fullWidth = false,
  noPadding = false,
  skeleton = false,
  tags,
  footer,
  onRetry,
}) => {
  const isMobile = useIsMobile();

  // 渲染面包屑
  const renderBreadcrumb = () => {
    if (!breadcrumb || breadcrumb.length === 0) return null;

    const items = [
      {
        title: (
          <Link to="/">
            <HomeOutlined />
          </Link>
        ),
      },
      ...breadcrumb.map((item, index) => ({
        title: item.path ? (
          <Link to={item.path}>
            {item.icon}
            {item.icon && <span style={{ marginLeft: 4 }}>{item.title}</span>}
            {!item.icon && item.title}
          </Link>
        ) : (
          <span>
            {item.icon}
            {item.icon && <span style={{ marginLeft: 4 }}>{item.title}</span>}
            {!item.icon && item.title}
          </span>
        ),
      })),
    ];

    return (
      <Breadcrumb
        className="page-container-breadcrumb"
        items={items}
      />
    );
  };

  // 渲染页面头部
  const renderHeader = () => {
    const hasExtra = extra && React.Children.count(extra) > 0;

    return (
      <div className={`page-container-header ${isMobile ? 'page-container-header--mobile' : ''}`}>
        <div className="page-container-header-main">
          <div className="page-container-header-left">
            <h1 className="page-container-title">{title}</h1>
            {tags && <div className="page-container-tags">{tags}</div>}
            {description && (
              <p className="page-container-description">{description}</p>
            )}
          </div>
          {hasExtra && (
            <div className="page-container-header-right">
              {extra}
            </div>
          )}
        </div>
      </div>
    );
  };

  // 渲染加载状态
  const renderLoading = () => {
    if (skeleton) {
      return (
        <div className="page-container-skeleton">
          <Skeleton active paragraph={{ rows: 4 }} />
          <Skeleton active paragraph={{ rows: 4 }} />
        </div>
      );
    }

    return (
      <div className="page-container-loading">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  };

  // 渲染错误状态
  const renderError = () => {
    return (
      <div className="page-container-error">
        <Alert
          type="error"
          message="加载失败"
          description={error}
          showIcon
          action={
            onRetry && (
              <button
                className="page-container-retry-btn"
                onClick={onRetry}
              >
                重试
              </button>
            )
          }
        />
      </div>
    );
  };

  // 渲染内容
  const renderContent = () => {
    if (loading) {
      return renderLoading();
    }

    if (error) {
      return renderError();
    }

    return children;
  };

  // 组合类名
  const containerClassName = [
    'page-container',
    fullWidth ? 'page-container--full-width' : '',
    noPadding ? 'page-container--no-padding' : '',
    isMobile ? 'page-container--mobile' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={containerClassName}>
      {renderBreadcrumb()}
      {renderHeader()}
      <div className="page-container-content">
        {renderContent()}
      </div>
      {footer && (
        <div className="page-container-footer">
          {footer}
        </div>
      )}
    </div>
  );
};

export default PageContainer;
