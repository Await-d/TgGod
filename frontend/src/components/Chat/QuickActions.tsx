import React, { useState } from 'react';
import { Space, Button, Tooltip, Divider, Badge } from 'antd';
import { 
  FilterOutlined,
  SyncOutlined,
  PlusOutlined,
  SettingOutlined,
  SearchOutlined,
  DownloadOutlined,
  ReloadOutlined,
  CalendarOutlined,
  CheckSquareOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../../types';
import { QuickActionsProps, MessageFilter } from '../../types/chat';
import { isEmptyFilter, getFilterDescription } from '../../utils/filterUtils';
import MonthlySyncModal from '../MonthlySyncModal';

interface ExtendedQuickActionsProps extends QuickActionsProps {
  isMobile?: boolean;
  onSearch?: () => void;
  onDownload?: () => void;
  onSettings?: () => void;
  onRefresh?: () => void;
  loading?: boolean;
  allGroups?: TelegramGroup[];
  currentFilter?: MessageFilter; // 当前筛选条件
  onClearFilter?: () => void; // 清除筛选条件回调
  // 🔥 新增：批量下载相关属性
  selectionMode?: boolean;
  selectedMessages?: Set<number>;
  onToggleSelection?: () => void;
  onBatchDownload?: (force?: boolean) => void;
  onSelectAllMedia?: () => void;
  batchDownloading?: boolean;
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
  allGroups = [],
  currentFilter,
  onClearFilter,
  // 🔥 新增：批量下载相关props
  selectionMode = false,
  selectedMessages = new Set<number>(),
  onToggleSelection,
  onBatchDownload,
  onSelectAllMedia,
  batchDownloading = false
}) => {
  const [monthlySyncVisible, setMonthlySyncVisible] = useState(false);

  // 检查是否有活跃的筛选条件
  const hasActiveFilter = currentFilter && !isEmptyFilter(currentFilter);
  const filterDescription = currentFilter ? getFilterDescription(currentFilter) : '';

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
            
            <Tooltip title={hasActiveFilter ? `筛选: ${filterDescription}` : "筛选消息"}>
              <Badge dot={hasActiveFilter} offset={[-2, 2]}>
                <Button
                  type={hasActiveFilter ? "primary" : "text"}
                  icon={<FilterOutlined />}
                  onClick={onFilter}
                  size="small"
                />
              </Badge>
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
            
            {/* 🔥 批量下载切换按钮 */}
            <Tooltip title={selectionMode ? "退出选择模式" : "多选下载"}>
              <Badge count={selectedMessages.size} size="small" offset={[-2, 2]}>
                <Button
                  type={selectionMode ? "primary" : "text"}
                  icon={<CheckSquareOutlined />}
                  onClick={onToggleSelection}
                  size="small"
                  loading={batchDownloading}
                />
              </Badge>
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
          
          <Tooltip title={hasActiveFilter ? `筛选: ${filterDescription}` : "筛选消息"}>
            <Badge dot={hasActiveFilter} offset={[-2, 2]}>
              <Button
                type={hasActiveFilter ? "primary" : "text"}
                icon={<FilterOutlined />}
                onClick={onFilter}
              >
                筛选
              </Button>
            </Badge>
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
          
          {/* 🔥 批量下载切换按钮 */}
          <Tooltip title={selectionMode ? "退出选择模式" : "多选下载"}>
            <Badge count={selectedMessages.size} size="small" offset={[-2, 2]}>
              <Button
                type={selectionMode ? "primary" : "text"}
                icon={<CheckSquareOutlined />}
                onClick={onToggleSelection}
                loading={batchDownloading}
              >
                {selectionMode ? `多选 (${selectedMessages.size})` : "多选"}
              </Button>
            </Badge>
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