import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  DatePicker,
  Select,
  Form,
  Space,
  Row,
  Col,
  Card,
  Typography,
  Progress,
  Alert,
  Tag,
  Divider,
  message,
  Spin,
  List,
  Timeline,
  Statistic
} from 'antd';
import {
  CalendarOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  WarningOutlined
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import { telegramApi } from '../services/apiService';
import { MonthInfo, MonthlySyncResponse, TelegramGroup } from '../types';
import { webSocketService } from '../services/websocket';

// 扩展dayjs功能
dayjs.extend(isSameOrBefore);

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

interface MonthlySyncModalProps {
  visible: boolean;
  onClose: () => void;
  selectedGroup?: TelegramGroup;
  groups: TelegramGroup[];
}

interface SyncProgress {
  currentMonth: string;
  progress: number;
  total: number;
  completed: number;
  failed: number;
}

const MonthlySyncModal: React.FC<MonthlySyncModalProps> = ({
  visible,
  onClose,
  selectedGroup,
  groups
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [syncProgress, setSyncProgress] = useState<SyncProgress | null>(null);
  const [syncResult, setSyncResult] = useState<MonthlySyncResponse | null>(null);
  const [defaultMonths, setDefaultMonths] = useState<MonthInfo[]>([]);
  const [selectedMonths, setSelectedMonths] = useState<MonthInfo[]>([]);
  const [syncMode, setSyncMode] = useState<'single' | 'batch'>('single');
  const [selectedGroups, setSelectedGroups] = useState<number[]>([]);

  // 获取默认同步月份
  useEffect(() => {
    if (visible && selectedGroup) {
      loadDefaultMonths();
      
      // 订阅WebSocket进度更新
      const unsubscribe = webSocketService.subscribe('monthly_sync_progress', (progressData) => {
        console.log('收到进度更新:', progressData);
        setSyncProgress({
          currentMonth: progressData.currentMonth,
          progress: progressData.progress + 1, // 显示当前正在处理的月份
          total: progressData.total,
          completed: progressData.completed,
          failed: progressData.failed
        });
      });

      // 订阅同步完成事件
      const unsubscribeComplete = webSocketService.subscribe('monthly_sync_complete', (result) => {
        console.log('收到同步完成:', result);
        setSyncResult(result);
        setSyncProgress(null);
        setLoading(false);
        
        if (result.success) {
          message.success(`同步完成！共同步 ${result.total_messages} 条消息`);
        } else {
          message.error('同步失败：' + result.error);
        }
      });

      // 确保WebSocket已连接
      if (!webSocketService.isConnected()) {
        console.log('WebSocket未连接，尝试连接...');
        webSocketService.connect();
      }

      return () => {
        unsubscribe();
        unsubscribeComplete();
      };
    }
  }, [visible, selectedGroup]);

  const loadDefaultMonths = async () => {
    if (!selectedGroup) return;
    
    try {
      const response = await telegramApi.getDefaultSyncMonths(selectedGroup.id, 3);
      setDefaultMonths(response.months);
      setSelectedMonths(response.months);
    } catch (error) {
      console.error('获取默认同步月份失败:', error);
    }
  };

  // 生成月份选项
  const generateMonthOptions = (months: number = 12) => {
    const options: MonthInfo[] = [];
    const now = dayjs();
    
    for (let i = 0; i < months; i++) {
      const date = now.subtract(i, 'month');
      options.push({
        year: date.year(),
        month: date.month() + 1
      });
    }
    
    return options;
  };

  const monthOptions = generateMonthOptions(12);

  // 处理快速选择
  const handleQuickSelect = (type: 'recent3' | 'recent6' | 'recent12') => {
    const counts = { recent3: 3, recent6: 6, recent12: 12 };
    const count = counts[type];
    const months = generateMonthOptions(count);
    setSelectedMonths(months);
    form.setFieldsValue({ months });
  };

  // 处理自定义日期范围选择
  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (!dates || !dates[0] || !dates[1]) {
      setSelectedMonths([]);
      return;
    }

    const [start, end] = dates;
    const months: MonthInfo[] = [];
    
    let current = start.startOf('month');
    const endMonth = end.endOf('month');
    
    while (current.isSameOrBefore(endMonth, 'month')) {
      months.push({
        year: current.year(),
        month: current.month() + 1
      });
      current = current.add(1, 'month');
    }
    
    setSelectedMonths(months);
    form.setFieldsValue({ months });
  };

  // 执行同步
  const handleSync = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      setSyncResult(null);
      setSyncProgress({
        currentMonth: '准备开始...',
        progress: 0,
        total: selectedMonths.length,
        completed: 0,
        failed: 0
      });

      if (syncMode === 'single' && selectedGroup) {
        // 单个群组同步 - 启动异步任务
        const response = await telegramApi.syncGroupMessagesMonthly(
          selectedGroup.id,
          selectedMonths
        );
        
        if (response.success) {
          message.success(response.message);
          setSyncProgress({
            currentMonth: '等待开始...',
            progress: 0,
            total: selectedMonths.length,
            completed: 0,
            failed: 0
          });
        } else {
          throw new Error('启动同步任务失败');
        }
      } else if (syncMode === 'batch' && selectedGroups.length > 0) {
        // 批量群组同步
        const result = await telegramApi.syncAllGroupsMonthly(selectedMonths);
        
        if (result.success) {
          message.success(`批量同步任务已启动`);
        } else {
          throw new Error('启动批量同步失败');
        }
      } else {
        message.error('请选择要同步的群组');
        setLoading(false);
        setSyncProgress(null);
        return;
      }

      // API调用成功，现在等待WebSocket消息
      // loading状态会在收到完成消息时被重置

    } catch (error) {
      console.error('启动同步失败:', error);
      message.error('启动同步任务失败，请重试');
      setLoading(false);
      setSyncProgress(null);
    }
  };

  // 取消同步
  const handleCancelSync = () => {
    setLoading(false);
    setSyncProgress(null);
    setSyncResult(null);
    message.info('已取消同步任务');
  };

  // 格式化月份显示
  const formatMonth = (month: MonthInfo) => {
    return `${month.year}-${month.month.toString().padStart(2, '0')}`;
  };

  // 重置表单
  const handleReset = () => {
    form.resetFields();
    setSyncResult(null);
    setSyncProgress(null);
    setSelectedMonths(defaultMonths);
    setSyncMode('single');
    setSelectedGroups([]);
  };

  return (
    <Modal
      title={
        <Space>
          <CalendarOutlined />
          <span>按月同步群组消息</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={800}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSync}
        initialValues={{ months: defaultMonths }}
      >
        {/* 同步模式选择 */}
        <Form.Item label="同步模式">
          <Select
            value={syncMode}
            onChange={setSyncMode}
            style={{ width: 200 }}
          >
            <Select.Option value="single">单个群组同步</Select.Option>
            <Select.Option value="batch">批量群组同步</Select.Option>
          </Select>
        </Form.Item>

        {/* 群组选择 */}
        {syncMode === 'single' && (
          <Form.Item label="目标群组">
            <Card size="small">
              <Row align="middle">
                <Col flex="auto">
                  <Space>
                    <Text strong>{selectedGroup?.title}</Text>
                    <Tag color="blue">
                      {selectedGroup?.member_count || 0} 成员
                    </Tag>
                  </Space>
                </Col>
                <Col>
                  <Text type="secondary">
                    @{selectedGroup?.username || '未知'}
                  </Text>
                </Col>
              </Row>
            </Card>
          </Form.Item>
        )}

        {syncMode === 'batch' && (
          <Form.Item label="选择群组" name="groups">
            <Select
              mode="multiple"
              placeholder="选择要同步的群组"
              value={selectedGroups}
              onChange={setSelectedGroups}
              style={{ width: '100%' }}
            >
              {groups.map(group => (
                <Select.Option key={group.id} value={group.id}>
                  {group.title} (@{group.username})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        )}

        {/* 快速选择 */}
        <Form.Item label="快速选择">
          <Space wrap>
            <Button
              type="default"
              onClick={() => handleQuickSelect('recent3')}
              icon={<CalendarOutlined />}
            >
              最近3个月
            </Button>
            <Button
              type="default"
              onClick={() => handleQuickSelect('recent6')}
              icon={<CalendarOutlined />}
            >
              最近6个月
            </Button>
            <Button
              type="default"
              onClick={() => handleQuickSelect('recent12')}
              icon={<CalendarOutlined />}
            >
              最近12个月
            </Button>
          </Space>
        </Form.Item>

        {/* 自定义日期范围 */}
        <Form.Item label="自定义日期范围">
          <RangePicker
            picker="month"
            onChange={handleDateRangeChange}
            style={{ width: '100%' }}
            placeholder={['开始月份', '结束月份']}
          />
        </Form.Item>

        {/* 选中的月份预览 */}
        {selectedMonths.length > 0 && (
          <Form.Item label="选中的月份">
            <Card size="small">
              <Space wrap>
                {selectedMonths.map((month, index) => (
                  <Tag key={index} color="blue">
                    {formatMonth(month)}
                  </Tag>
                ))}
              </Space>
              <Divider />
              <Text type="secondary">
                共选择 {selectedMonths.length} 个月，预计同步时间：
                {Math.ceil(selectedMonths.length * 0.5)} 分钟
              </Text>
            </Card>
          </Form.Item>
        )}

        {/* 同步进度 */}
        {syncProgress && (
          <Form.Item label="同步进度">
            <Card size="small">
              <Progress
                percent={Math.round((syncProgress.progress / syncProgress.total) * 100)}
                status="active"
                format={() => `${syncProgress.progress}/${syncProgress.total}`}
              />
              <Space style={{ marginTop: 8 }}>
                <Text>当前: {syncProgress.currentMonth}</Text>
                <Text type="success">完成: {syncProgress.completed}</Text>
                <Text type="danger">失败: {syncProgress.failed}</Text>
              </Space>
            </Card>
          </Form.Item>
        )}

        {/* 同步结果 */}
        {syncResult && (
          <Form.Item label="同步结果">
            <Card size="small">
              <Row gutter={16}>
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
                    value={Math.round((syncResult.months_synced / selectedMonths.length) * 100)}
                    suffix="%"
                    prefix={<CheckCircleOutlined />}
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Col>
              </Row>

              {/* 详细统计 */}
              {syncResult.monthly_stats.length > 0 && (
                <>
                  <Divider />
                  <Title level={5}>详细统计</Title>
                  <Timeline
                    items={syncResult.monthly_stats.map(stat => ({
                      color: stat.saved_messages > 0 ? 'green' : 'red',
                      dot: stat.saved_messages > 0 ? 
                        <CheckCircleOutlined /> : 
                        <ExclamationCircleOutlined />,
                      children: (
                        <div>
                          <Text strong>{formatMonth(stat)}</Text>
                          <br />
                          <Text>
                            同步 {stat.saved_messages} / {stat.total_messages} 条消息
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
                  <Divider />
                  <Alert
                    type="warning"
                    message="部分月份同步失败"
                    description={
                      <List
                        size="small"
                        dataSource={syncResult.failed_months}
                        renderItem={(item) => (
                          <List.Item>
                            <Space>
                              <WarningOutlined />
                              <Text>{formatMonth(item.month)}</Text>
                              <Text type="danger">{item.error}</Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    }
                  />
                </>
              )}
            </Card>
          </Form.Item>
        )}

        {/* 操作按钮 */}
        <Form.Item>
          <Space>
            {!loading ? (
              <Button
                type="primary"
                htmlType="submit"
                disabled={selectedMonths.length === 0}
                icon={<SyncOutlined />}
              >
                开始同步
              </Button>
            ) : (
              <Button
                type="primary"
                danger
                onClick={handleCancelSync}
                icon={<SyncOutlined />}
              >
                取消同步
              </Button>
            )}
            <Button onClick={handleReset} disabled={loading}>
              重置
            </Button>
            <Button onClick={onClose} disabled={loading}>
              关闭
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default MonthlySyncModal;