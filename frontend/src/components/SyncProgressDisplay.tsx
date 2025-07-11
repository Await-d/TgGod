import React from 'react';
import { Card, Progress, Space, Typography, Tag, Button, Timeline, Statistic, Row, Col } from 'antd';
import { 
  CheckCircleOutlined, 
  ExclamationCircleOutlined, 
  SyncOutlined, 
  CloseOutlined,
  CalendarOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import { MonthlySyncResponse, MonthInfo } from '../types';

const { Title, Text } = Typography;

interface SyncProgressDisplayProps {
  syncResult: MonthlySyncResponse;
  onClose: () => void;
  isActive?: boolean;
}

const SyncProgressDisplay: React.FC<SyncProgressDisplayProps> = ({
  syncResult,
  onClose,
  isActive = false
}) => {
  // 格式化月份显示
  const formatMonth = (year: number, month: number) => {
    return `${year}-${month.toString().padStart(2, '0')}`;
  };

  // 计算成功率
  const successRate = syncResult.months_synced > 0 ? 
    Math.round((syncResult.months_synced / (syncResult.months_synced + syncResult.failed_months.length)) * 100) : 0;

  return (
    <Card
      title={
        <Space>
          <CalendarOutlined />
          <span>按月同步结果</span>
          {isActive && <SyncOutlined spin />}
        </Space>
      }
      extra={
        <Button
          type="text"
          icon={<CloseOutlined />}
          onClick={onClose}
        />
      }
      style={{ marginBottom: 16 }}
    >
      {/* 总体统计 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Statistic
            title="总消息数"
            value={syncResult.total_messages}
            prefix={<DownloadOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="成功月份"
            value={syncResult.months_synced}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ color: '#3f8600' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="失败月份"
            value={syncResult.failed_months.length}
            prefix={<ExclamationCircleOutlined />}
            valueStyle={{ color: '#cf1322' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="成功率"
            value={successRate}
            suffix="%"
            prefix={<CheckCircleOutlined />}
            valueStyle={{ color: '#3f8600' }}
          />
        </Col>
      </Row>

      {/* 进度条 */}
      <Progress
        percent={successRate}
        status={syncResult.success ? 'success' : 'exception'}
        strokeColor={{
          '0%': '#108ee9',
          '100%': '#87d068',
        }}
        style={{ marginBottom: 16 }}
      />

      {/* 详细统计时间线 */}
      {syncResult.monthly_stats.length > 0 && (
        <>
          <Title level={5}>月份详情</Title>
          <Timeline
            style={{ marginBottom: 16 }}
            items={syncResult.monthly_stats.map(stat => ({
              color: stat.saved_messages > 0 ? 'green' : 'red',
              dot: stat.saved_messages > 0 ? 
                <CheckCircleOutlined style={{ fontSize: '16px' }} /> : 
                <ExclamationCircleOutlined style={{ fontSize: '16px' }} />,
              children: (
                <div>
                  <Space>
                    <Text strong>{formatMonth(stat.year, stat.month)}</Text>
                    <Tag color={stat.saved_messages > 0 ? 'success' : 'error'}>
                      {stat.saved_messages} / {stat.total_messages}
                    </Tag>
                  </Space>
                  <br />
                  <Text type="secondary">
                    时间范围: {new Date(stat.start_date).toLocaleDateString()} - {new Date(stat.end_date).toLocaleDateString()}
                  </Text>
                </div>
              )
            }))}
          />
        </>
      )}

      {/* 失败详情 */}
      {syncResult.failed_months.length > 0 && (
        <>
          <Title level={5}>失败详情</Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            {syncResult.failed_months.map((failed, index) => (
              <Card key={index} size="small" style={{ backgroundColor: '#fff2f0' }}>
                <Space>
                  <ExclamationCircleOutlined style={{ color: '#cf1322' }} />
                  <Text strong>{formatMonth(failed.month.year, failed.month.month)}</Text>
                  <Text type="danger">{failed.error}</Text>
                </Space>
              </Card>
            ))}
          </Space>
        </>
      )}
    </Card>
  );
};

export default SyncProgressDisplay;