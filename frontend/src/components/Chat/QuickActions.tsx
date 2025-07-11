import React from 'react';
import { Space, Button, Tooltip, Divider } from 'antd';
import { 
  FilterOutlined,
  SyncOutlined,
  PlusOutlined,
  SettingOutlined,
  SearchOutlined,
  DownloadOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { QuickActionsProps } from '../../types/chat';
// 移除不再需要的导入

interface ExtendedQuickActionsProps extends QuickActionsProps {
  isMobile?: boolean;
  onSearch?: () => void;
  onDownload?: () => void;
  onSettings?: () => void;
  onRefresh?: () => void;
  loading?: boolean;
}

const QuickActions: React.FC<ExtendedQuickActionsProps> = ({
  selectedGroup,
  onFilter,
  onSync,
  onCreateRule,
  isMobile = false,
  onSearch,
  onDownload,
  onSettings,
  onRefresh,
  loading = false
}) => {
  
  // 如果没有选择群组，不显示操作按钮
  if (!selectedGroup) {
    return null;
  }

  // 处理同步消息 - 现在由父组件管理
  const handleSync = () => {
    onSync?.();
  };

  // 移动端显示精简版按钮
  if (isMobile) {
    return (
      <div className="quick-actions mobile">
        <Space size="small" split={<Divider type="vertical" />}>
          <Tooltip title="刷新消息">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={onRefresh}
              loading={loading}
              size="small"
            />
          </Tooltip>
          
          <Tooltip title="筛选消息">
            <Button
              type="text"
              icon={<FilterOutlined />}
              onClick={onFilter}
              size="small"
            />
          </Tooltip>
          
          <Tooltip title="创建规则">
            <Button
              type="text"
              icon={<PlusOutlined />}
              onClick={onCreateRule}
              size="small"
              style={{ color: '#1890ff' }}
            />
          </Tooltip>
          
          <Tooltip title="同步消息">
            <Button
              type="text"
              icon={<SyncOutlined />}
              onClick={handleSync}
              size="small"
            />
          </Tooltip>
        </Space>
      </div>
    );
  }

  // 桌面端显示完整按钮
  return (
    <div className="quick-actions desktop">
      <Space size="small" wrap>
        <Tooltip title="刷新消息">
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={onRefresh}
            loading={loading}
          >
            刷新
          </Button>
        </Tooltip>
        
        <Tooltip title="搜索消息">
          <Button
            type="text"
            icon={<SearchOutlined />}
            onClick={onSearch}
          >
            搜索
          </Button>
        </Tooltip>
        
        <Tooltip title="筛选消息">
          <Button
            type="text"
            icon={<FilterOutlined />}
            onClick={onFilter}
          >
            筛选
          </Button>
        </Tooltip>
        
        <Divider type="vertical" />
        
        <Tooltip title="创建下载规则">
          <Button
            type="text"
            icon={<PlusOutlined />}
            onClick={onCreateRule}
            style={{ color: '#1890ff' }}
          >
            创建规则
          </Button>
        </Tooltip>
        
        <Tooltip title="下载消息">
          <Button
            type="text"
            icon={<DownloadOutlined />}
            onClick={onDownload}
          >
            下载
          </Button>
        </Tooltip>
        
        <Divider type="vertical" />
        
        <Tooltip title="同步消息">
          <Button
            type="text"
            icon={<SyncOutlined />}
            onClick={handleSync}
          >
            同步
          </Button>
        </Tooltip>
        
        <Tooltip title="群组设置">
          <Button
            type="text"
            icon={<SettingOutlined />}
            onClick={onSettings}
          >
            设置
          </Button>
        </Tooltip>
      </Space>
    </div>
  );
};

export default QuickActions;