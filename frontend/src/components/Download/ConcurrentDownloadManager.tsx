import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Progress,
  List,
  Tag,
  Space,
  Statistic,
  Row,
  Col,
  notification,
  Popconfirm,
  Tooltip,
  Badge
} from 'antd';
import {
  DownloadOutlined,
  CloseOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  RocketOutlined
  // PauseOutlined // 已移除未使用的导入
} from '@ant-design/icons';
import { mediaApi } from '../../services/apiService';

interface DownloadStats {
  total_active_downloads: number;
  user_active_downloads: Record<string, number>;
  max_concurrent_downloads: number;
  user_concurrent_limit: number;
  started_at: string | null;
  current_downloads: number[];
  available_slots: number;
}

interface ConcurrentDownloadManagerProps {
  className?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const ConcurrentDownloadManager: React.FC<ConcurrentDownloadManagerProps> = ({
  className = '',
  autoRefresh = true,
  refreshInterval = 3000
}) => {
  const [stats, setStats] = useState<DownloadStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshTimer, setRefreshTimer] = useState<NodeJS.Timeout | null>(null);

  // 获取下载统计
  const fetchDownloadStats = useCallback(async () => {
    try {
      setLoading(true);
      const response = await mediaApi.getDownloadStats();
      setStats(response.stats);
    } catch (error: any) {
      console.error('获取下载统计失败:', error);
      notification.error({
        message: '获取下载统计失败',
        description: error.message || '未知错误'
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // 取消单个下载
  const handleCancelDownload = async (messageId: number) => {
    try {
      await mediaApi.cancelConcurrentDownload(messageId);
      notification.success({
        message: '下载已取消',
        description: `消息 ${messageId} 的下载已取消`
      });

      // 刷新统计
      await fetchDownloadStats();
    } catch (error: any) {
      console.error('取消下载失败:', error);
      notification.error({
        message: '取消下载失败',
        description: error.message || '未知错误'
      });
    }
  };

  // 批量取消所有下载
  const handleCancelAllDownloads = async () => {
    if (!stats || stats.current_downloads.length === 0) return;

    try {
      // 逐个取消所有下载
      const cancelPromises = stats.current_downloads.map(messageId =>
        mediaApi.cancelConcurrentDownload(messageId).catch(error => ({
          messageId,
          error: error.message
        }))
      );

      const results = await Promise.all(cancelPromises);
      const successful = results.filter(result => !('error' in result)).length;
      const failed = results.length - successful;

      notification.success({
        message: '批量取消完成',
        description: `成功取消 ${successful} 个下载${failed > 0 ? `，失败 ${failed} 个` : ''}`
      });

      // 刷新统计
      await fetchDownloadStats();
    } catch (error: any) {
      notification.error({
        message: '批量取消失败',
        description: error.message || '未知错误'
      });
    }
  };

  // 自动刷新
  useEffect(() => {
    fetchDownloadStats();

    if (autoRefresh) {
      const timer = setInterval(fetchDownloadStats, refreshInterval);
      setRefreshTimer(timer);

      return () => {
        if (timer) clearInterval(timer);
      };
    }
  }, [fetchDownloadStats, autoRefresh, refreshInterval]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (refreshTimer) {
        clearInterval(refreshTimer);
      }
    };
  }, [refreshTimer]);

  const formatDuration = (startedAt: string | null) => {
    if (!startedAt) return '未开始';
    
    const start = new Date(startedAt);
    const now = new Date();
    const diffMs = now.getTime() - start.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffSecs = Math.floor((diffMs % 60000) / 1000);
    
    if (diffMins > 0) {
      return `${diffMins}分${diffSecs}秒`;
    }
    return `${diffSecs}秒`;
  };

  const calculateUsagePercent = () => {
    if (!stats) return 0;
    return Math.round((stats.total_active_downloads / stats.max_concurrent_downloads) * 100);
  };

  const getStatusColor = () => {
    const percent = calculateUsagePercent();
    if (percent >= 90) return '#ff4d4f'; // 红色：接近满载
    if (percent >= 70) return '#faad14'; // 橙色：高负载
    if (percent >= 30) return '#52c41a'; // 绿色：正常
    return '#1890ff'; // 蓝色：低负载
  };

  return (
    <div className={`concurrent-download-manager ${className}`}>
      <Card 
        title={
          <Space>
            <RocketOutlined />
            并发下载管理器
            {stats && stats.total_active_downloads > 0 && (
              <Badge count={stats.total_active_downloads} showZero />
            )}
          </Space>
        }
        extra={
          <Space>
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={fetchDownloadStats}
              loading={loading}
            >
              刷新
            </Button>
            {stats && stats.current_downloads.length > 0 && (
              <Popconfirm
                title="确定取消所有下载？"
                description="这将取消当前所有正在进行的下载任务"
                onConfirm={handleCancelAllDownloads}
                okText="确定"
                cancelText="取消"
              >
                <Button type="primary" danger size="small">
                  取消全部
                </Button>
              </Popconfirm>
            )}
          </Space>
        }
        loading={loading}
      >
        {stats ? (
          <>
            {/* 统计信息 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={24} sm={6}>
                <Card size="small">
                  <Statistic
                    title="活跃下载"
                    value={stats.total_active_downloads}
                    suffix={`/ ${stats.max_concurrent_downloads}`}
                    valueStyle={{ color: getStatusColor() }}
                    prefix={<DownloadOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={6}>
                <Card size="small">
                  <Statistic
                    title="可用插槽"
                    value={stats.available_slots}
                    valueStyle={{ 
                      color: stats.available_slots > 0 ? '#52c41a' : '#ff4d4f' 
                    }}
                    prefix={<InfoCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={6}>
                <Card size="small">
                  <Statistic
                    title="并发使用率"
                    value={calculateUsagePercent()}
                    suffix="%"
                    valueStyle={{ color: getStatusColor() }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={6}>
                <Card size="small">
                  <Statistic
                    title="运行时长"
                    value={formatDuration(stats.started_at)}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* 并发使用率进度条 */}
            <div style={{ marginBottom: 16 }}>
              <Progress
                percent={calculateUsagePercent()}
                strokeColor={getStatusColor()}
                format={(percent) => `${stats.total_active_downloads}/${stats.max_concurrent_downloads} (${percent}%)`}
              />
            </div>

            {/* 当前下载列表 */}
            {stats.current_downloads.length > 0 ? (
              <div>
                <h4>当前下载任务 ({stats.current_downloads.length})</h4>
                <List
                  size="small"
                  dataSource={stats.current_downloads}
                  renderItem={(messageId) => (
                    <List.Item
                      actions={[
                        <Tooltip title="取消下载">
                          <Button
                            type="text"
                            size="small"
                            danger
                            icon={<CloseOutlined />}
                            onClick={() => handleCancelDownload(messageId)}
                          />
                        </Tooltip>
                      ]}
                    >
                      <Space>
                        <Tag color="processing">下载中</Tag>
                        <span>消息 ID: {messageId}</span>
                      </Space>
                    </List.Item>
                  )}
                />
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                🎉 当前没有活跃的下载任务
              </div>
            )}

            {/* 用户下载统计 */}
            {Object.keys(stats.user_active_downloads).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <h4>用户下载统计</h4>
                <Space wrap>
                  {Object.entries(stats.user_active_downloads).map(([userId, count]) => (
                    <Tag key={userId} color="blue">
                      用户 {userId}: {count} 个下载
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <InfoCircleOutlined style={{ fontSize: 48, color: '#ccc' }} />
            <p style={{ marginTop: 16, color: '#999' }}>
              加载下载统计中...
            </p>
          </div>
        )}
      </Card>
    </div>
  );
};

export default ConcurrentDownloadManager;