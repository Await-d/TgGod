import React, { useState } from 'react';
import { Space, Button, Tooltip, Divider } from 'antd';
import { 
  FilterOutlined,
  SyncOutlined,
  PlusOutlined,
  SettingOutlined,
  SearchOutlined,
  DownloadOutlined,
  ReloadOutlined,
  CalendarOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { QuickActionsProps } from '../../types/chat';
import MonthlySyncModal from '../MonthlySyncModal';

interface ExtendedQuickActionsProps extends QuickActionsProps {
  isMobile?: boolean;
  onSearch?: () => void;
  onDownload?: () => void;
  onSettings?: () => void;
  onRefresh?: () => void;
  loading?: boolean;
  allGroups?: TelegramGroup[]; // 添加所有群组列表
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
  loading = false,
  allGroups = []
}) => {
  const [monthlySyncVisible, setMonthlySyncVisible] = useState(false);

  const handleMonthlySync = () => {
    setMonthlySyncVisible(true);
  };

  const handleMonthlySyncClose = () => {
    setMonthlySyncVisible(false);
  };
  
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
      <>
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
              />
            </Tooltip>
            
            <Tooltip title="同步消息">
              <Button
                type="text"
                icon={<SyncOutlined />}
                onClick={handleSync}
                loading={loading}
                size="small"
              />
            </Tooltip>

            <Tooltip title="按月同步">
              <Button
                type="text"
                icon={<CalendarOutlined />}
                onClick={handleMonthlySync}
                size="small"
              />
            </Tooltip>
          </Space>
        </div>

        <MonthlySyncModal
          visible={monthlySyncVisible}
          onClose={handleMonthlySyncClose}
          selectedGroup={selectedGroup}
          groups={allGroups}
        />
      </>
    );
  }

  // 桌面端显示完整版按钮
  return (
    <>
      <div className="quick-actions desktop">
        <Space split={<Divider type="vertical" />}>
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
          
          <Tooltip title="创建规则">
            <Button
              type="text"
              icon={<PlusOutlined />}
              onClick={onCreateRule}
            >
              创建规则
            </Button>
          </Tooltip>
          
          <Tooltip title="同步消息">
            <Button
              type="text"
              icon={<SyncOutlined />}
              onClick={handleSync}
              loading={loading}
            >
              同步
            </Button>
          </Tooltip>

          <Tooltip title="按月同步">
            <Button
              type="text"
              icon={<CalendarOutlined />}
              onClick={handleMonthlySync}
            >
              按月同步
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
          
          <Tooltip title="设置">
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={onSettings}
            />
          </Tooltip>

          <Tooltip title="刷新">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={onRefresh}
              loading={loading}
            />
          </Tooltip>
        </Space>
      </div>

      <MonthlySyncModal
        visible={monthlySyncVisible}
        onClose={handleMonthlySyncClose}
        selectedGroup={selectedGroup}
        groups={allGroups}
      />
    </>
  );
};

export default QuickActions;