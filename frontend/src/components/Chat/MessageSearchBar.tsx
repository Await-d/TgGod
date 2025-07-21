import React from 'react';
import { Input, Button, Space, Tooltip } from 'antd';
import {
    SearchOutlined,
    FilterOutlined,
    SyncOutlined,
    ClearOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import './MessageSearchBar.css';

interface MessageSearchBarProps {
    onSearch: (query: string) => void;
    onFilter: () => void;
    onClear: () => void;
    onSync: () => void;
    onJumpToMessage?: (messageId: number) => void;
    query?: string;
    filter?: any;
    selectedGroup: TelegramGroup | null;
    loading?: boolean;
    isMobile?: boolean;
}

const MessageSearchBar: React.FC<MessageSearchBarProps> = ({
    onSearch,
    onFilter,
    onClear,
    onSync,
    onJumpToMessage,
    query = '',
    filter = {},
    selectedGroup,
    loading = false,
    isMobile = false
}) => {
    // 处理搜索输入
    const handleSearchInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        onSearch(e.target.value);
    };

    // 处理搜索框清空
    const handleClearSearch = () => {
        onClear();
    };

    // 处理跳转到指定消息ID
    const handleJumpToMessage = () => {
        // 提取数字作为消息ID
        const match = query.match(/\d+/);
        if (match && onJumpToMessage) {
            const messageId = parseInt(match[0], 10);
            if (!isNaN(messageId)) {
                onJumpToMessage(messageId);
            }
        }
    };

    // 检查查询是否可能是消息ID
    const isPossibleMessageId = /^\s*\d+\s*$/.test(query);

    return (
        <div className={`message-search-bar ${isMobile ? 'mobile' : ''}`}>
            <Input
                placeholder="搜索消息..."
                value={query}
                onChange={handleSearchInput}
                prefix={<SearchOutlined />}
                suffix={
                    query ? (
                        <ClearOutlined onClick={handleClearSearch} style={{ cursor: 'pointer' }} />
                    ) : null
                }
                onPressEnter={() => isPossibleMessageId ? handleJumpToMessage() : null}
            />
            <Space size="small">
                {isPossibleMessageId && onJumpToMessage && (
                    <Tooltip title="跳转到消息ID">
                        <Button
                            type="primary"
                            icon={<SearchOutlined />}
                            onClick={handleJumpToMessage}
                            size={isMobile ? 'small' : 'middle'}
                        >
                            跳转
                        </Button>
                    </Tooltip>
                )}
                <Tooltip title="筛选消息">
                    <Button
                        icon={<FilterOutlined />}
                        onClick={onFilter}
                        type={Object.keys(filter).length > 0 ? "primary" : "default"}
                        size={isMobile ? 'small' : 'middle'}
                    />
                </Tooltip>
                <Tooltip title="同步消息">
                    <Button
                        icon={<SyncOutlined spin={loading} />}
                        onClick={onSync}
                        disabled={!selectedGroup || loading}
                        size={isMobile ? 'small' : 'middle'}
                    />
                </Tooltip>
            </Space>
        </div>
    );
};

export default MessageSearchBar; 