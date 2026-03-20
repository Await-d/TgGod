import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Button, Upload, Popover } from 'antd';
import {
  SendOutlined,
  SmileOutlined,
  PaperClipOutlined,
  CloseCircleOutlined,
  FileImageOutlined,
  VideoCameraOutlined,
  FileOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import styles from './ChatInput.module.css';

interface ChatInputProps {
  onSend: (content: string, files?: File[]) => void;
  onUpload?: (files: File[]) => void;
  placeholder?: string;
  maxLength?: number;
  disabled?: boolean;
  loading?: boolean;
  className?: string;
}

const COMMON_EMOJIS = [
  '😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣',
  '😊', '😇', '🙂', '😉', '😍', '🥰', '😘', '😋',
  '🤔', '🤨', '😐', '😑', '😶', '🙄', '😏', '😣',
  '👍', '👎', '👌', '✌️', '🤞', '🤝', '👏', '🙌',
  '💪', '🙏', '❤️', '🧡', '💛', '💚', '💙', '💜',
];

const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  onUpload,
  placeholder = '输入消息...',
  maxLength = 4000,
  disabled = false,
  loading = false,
  className = '',
}) => {
  const [content, setContent] = useState('');
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [showEmoji, setShowEmoji] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-adjust textarea height
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [adjustHeight]);

  // Handle send message
  const handleSend = useCallback(() => {
    if (!content.trim() && fileList.length === 0) return;
    if (disabled || loading) return;

    const files = fileList.map((f) => f.originFileObj as File).filter(Boolean);
    onSend(content.trim(), files.length > 0 ? files : undefined);

    setContent('');
    setFileList([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [content, fileList, disabled, loading, onSend]);

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // Handle emoji selection
  const handleEmojiSelect = useCallback(
    (emoji: string) => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      setContent((prev) => prev.substring(0, start) + emoji + prev.substring(end));
      setShowEmoji(false);

      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(start + emoji.length, start + emoji.length);
      }, 0);
    },
    []
  );

  // Handle file upload
  const handleUploadChange: UploadProps['onChange'] = useCallback(
    ({ fileList: newFileList }: { fileList: UploadFile[] }) => {
      setFileList(newFileList);
      if (onUpload && newFileList.length > 0) {
        const files = newFileList
          .map((f: UploadFile) => f.originFileObj as File)
          .filter(Boolean);
        onUpload(files);
      }
    },
    [onUpload]
  );

  const uploadProps: UploadProps = {
    multiple: true,
    fileList,
    onChange: handleUploadChange,
    beforeUpload: () => false, // Prevent auto upload
    onRemove: (file) => {
      setFileList((prev) => prev.filter((f) => f.uid !== file.uid));
    },
    showUploadList: false,
  };

  // Get file icon based on type
  const getFileIcon = (type?: string) => {
    if (type?.startsWith('image/')) return <FileImageOutlined />;
    if (type?.startsWith('video/')) return <VideoCameraOutlined />;
    return <FileOutlined />;
  };

  // Emoji picker content
  const emojiContent = (
    <div className={styles.emojiPicker}>
      {COMMON_EMOJIS.map((emoji) => (
        <button
          key={emoji}
          className={styles.emojiButton}
          onClick={() => handleEmojiSelect(emoji)}
          type="button"
        >
          {emoji}
        </button>
      ))}
    </div>
  );

  return (
    <div className={`${styles.chatInput} ${className}`}>
      {/* File list preview */}
      {fileList.length > 0 && (
        <div className={styles.fileList}>
          {fileList.map((file) => (
            <div key={file.uid} className={styles.fileItem}>
              {getFileIcon(file.type)}
              <span className={styles.fileName}>{file.name}</span>
              <CloseCircleOutlined
                className={styles.removeFile}
                onClick={() =>
                  setFileList((prev) => prev.filter((f) => f.uid !== file.uid))
                }
              />
            </div>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className={styles.inputArea}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            adjustHeight();
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          maxLength={maxLength}
          rows={1}
        />

        <div className={styles.actions}>
          <Upload {...uploadProps}>
            <Button
              type="text"
              icon={<PaperClipOutlined />}
              className={styles.actionButton}
              disabled={disabled}
            />
          </Upload>

          <Popover
            content={emojiContent}
            trigger="click"
            open={showEmoji}
            onOpenChange={setShowEmoji}
            placement="topLeft"
          >
            <Button
              type="text"
              icon={<SmileOutlined />}
              className={styles.actionButton}
              disabled={disabled}
            />
          </Popover>

          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            disabled={disabled || (!content.trim() && fileList.length === 0)}
            className={styles.sendButton}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );
};

ChatInput.displayName = 'ChatInput';

export default ChatInput;
