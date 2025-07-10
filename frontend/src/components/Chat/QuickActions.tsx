import React from 'react';
import { Space, Button, Tooltip, Divider } from 'antd';
import { 
  FilterOutlined,
  SyncOutlined,
  PlusOutlined,
  SettingOutlined,
  SearchOutlined,
  DownloadOutlined 
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { QuickActionsProps } from '../../types/chat';

interface ExtendedQuickActionsProps extends QuickActionsProps {
  isMobile?: boolean;
  onSearch?: () => void;
  onDownload?: () => void;
  onSettings?: () => void;
}

const QuickActions: React.FC<ExtendedQuickActionsProps> = ({
  selectedGroup,
  onFilter,
  onSync,
  onCreateRule,
  isMobile = false,
  onSearch,
  onDownload,
  onSettings
}) => {
  
  // 如果没有选择群组，不显示操作按钮
  if (!selectedGroup) {
    return null;
  }

  // 移动端显示精简版按钮
  if (isMobile) {
    return (
      <div className="quick-actions mobile">
        <Space size="small" split={<Divider type="vertical" />}>
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
            />
          </Tooltip>
          
          <Tooltip title="同步消息">
            <Button
              type="text"
              icon={<SyncOutlined />}
              onClick={onSync}
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
            type="primary"
            icon={<PlusOutlined />}
            onClick={onCreateRule}
            ghost
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
            onClick={onSync}
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