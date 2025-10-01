import React from 'react';
import { Card, Space, Button, Typography } from 'antd';
import { LinkOutlined, ArrowRightOutlined } from '@ant-design/icons';
import './LinkPreview.css';

const { Text, Paragraph } = Typography;

interface LinkPreviewProps {
  url: string;
  title?: string;
  description?: string;
  className?: string;
}

// URL正则表达式
const URL_REGEX = /(https?:\/\/[^\s]+)/g;

// 格式化URL显示
const formatUrl = (url: string) => {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname + (urlObj.pathname !== '/' ? urlObj.pathname : '');
  } catch {
    return url;
  }
};

// 解析文本中的链接
export const parseLinks = (text: string) => {
  const links: string[] = [];
  let match;
  
  while ((match = URL_REGEX.exec(text)) !== null) {
    links.push(match[0]);
  }
  
  return links;
};

// 将文本中的链接转换为可点击的链接
export const renderTextWithLinks = (text: string) => {
  const parts = text.split(URL_REGEX);
  const links = parseLinks(text);
  let linkIndex = 0;
  
  return parts.map((part, index) => {
    if (URL_REGEX.test(part)) {
      const url = links[linkIndex++];
      return (
        <a
          key={index}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="message-link"
          onClick={(e) => {
            e.stopPropagation();
          }}
        >
          {formatUrl(url)}
        </a>
      );
    }
    return part;
  });
};

const LinkPreview: React.FC<LinkPreviewProps> = ({
  url,
  title,
  description,
  className
}) => {
  const handleOpenLink = () => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <Card
      size="small"
      className={`link-preview ${className || ''}`}
      hoverable
      onClick={handleOpenLink}
    >
      <Space direction="vertical" size={8} className="link-preview-content">
        <Space className="link-preview-header">
          <LinkOutlined className="link-preview-icon" />
          <Text strong ellipsis className="link-preview-title">
            {title || formatUrl(url)}
          </Text>
          <Button 
            type="text" 
            size="small" 
            icon={<ArrowRightOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              handleOpenLink();
            }}
          />
        </Space>
        
        {description && (
          <Paragraph 
            ellipsis={{ rows: 2 }} 
            className="link-preview-description"
            type="secondary"
          >
            {description}
          </Paragraph>
        )}
        
        <Text type="secondary" className="link-preview-url">
          {formatUrl(url)}
        </Text>
      </Space>
    </Card>
  );
};

export default LinkPreview;
