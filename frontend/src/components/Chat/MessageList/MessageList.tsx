import React, { useRef, useEffect, useCallback, useState } from 'react';
import { Spin, Empty, Button } from 'antd';
import { LoadingOutlined, ArrowUpOutlined } from '@ant-design/icons';
import MessageItem, { Message } from './MessageItem';
import styles from './MessageList.module.css';

interface MessageListProps {
  messages: Message[];
  loading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onMessageClick?: (message: Message) => void;
  onDownload?: (message: Message) => void;
  className?: string;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  loading = false,
  hasMore = false,
  onLoadMore,
  onMessageClick,
  onDownload,
  className
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);

  // Handle scroll
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;

    const { scrollTop } = containerRef.current;

    // Show scroll to top button
    setShowScrollTop(scrollTop > 300);

    // Load more when near top
    if (scrollTop < 100 && hasMore && !loading && onLoadMore) {
      onLoadMore();
    }
  }, [hasMore, loading, onLoadMore]);

  // Scroll to bottom on mount or new messages
  useEffect(() => {
    if (containerRef.current && messages.length > 0) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages.length]);

  // Scroll to top
  const scrollToTop = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, []);

  if (messages.length === 0 && !loading) {
    return (
      <div className={`${styles.messageList} ${className || ''}`}>
        <Empty description="暂无消息" />
      </div>
    );
  }

  return (
    <div className={`${styles.messageList} ${className || ''}`}>
      <div
        ref={containerRef}
        className={styles.scrollContainer}
        onScroll={handleScroll}
      >
        {loading && messages.length === 0 && (
          <div className={styles.loadingContainer}>
            <Spin indicator={<LoadingOutlined spin />} tip="加载中..." />
          </div>
        )}

        {hasMore && (
          <div className={styles.loadMoreTrigger}>
            {loading ? (
              <Spin size="small" />
            ) : (
              <Button type="link" onClick={onLoadMore}>
                加载更多
              </Button>
            )}
          </div>
        )}

        <div className={styles.messageContainer}>
          {messages.map((message) => (
            <MessageItem
              key={message.id}
              message={message}
              onClick={onMessageClick}
              onDownload={onDownload}
            />
          ))}
        </div>
      </div>

      {showScrollTop && (
        <Button
          className={styles.scrollTopButton}
          type="primary"
          shape="circle"
          icon={<ArrowUpOutlined />}
          onClick={scrollToTop}
        />
      )}
    </div>
  );
};

MessageList.displayName = 'MessageList';

export default MessageList;
