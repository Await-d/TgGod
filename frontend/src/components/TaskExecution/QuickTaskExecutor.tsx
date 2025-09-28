import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Select,
  Input,
  Space,
  message,
  Tooltip,
  Typography,
  Form,
  Row,
  Col,
  Modal,
  Alert,
  Progress,
  Badge,
  List,
  // Spin  // 未使用，已注释
} from 'antd';
import {
  PlayCircleOutlined,
  PlusOutlined,
  RocketOutlined,
  // CheckCircleOutlined,     // 暂时未使用
  // ExclamationCircleOutlined, // 暂时未使用
  // ClockCircleOutlined      // 暂时未使用
} from '@ant-design/icons';
import { taskApi, telegramApi, ruleApi } from '../../services/apiService';
import { DownloadTask, TelegramGroup, FilterRule } from '../../types';

const { Text /* Title */ } = Typography; // Title 暂时未使用
const { Option } = Select;

interface QuickTaskExecutorProps {
  onTaskCreated?: (task: DownloadTask) => void;
}

const QuickTaskExecutor: React.FC<QuickTaskExecutorProps> = ({ onTaskCreated }) => {
  const [loading, setLoading] = useState(false);
  const [groups, setGroups] = useState<TelegramGroup[]>([]);
  const [rules, setRules] = useState<FilterRule[]>([]);
  const [recentTasks, setRecentTasks] = useState<DownloadTask[]>([]);
  const [quickExecuteVisible, setQuickExecuteVisible] = useState(false);
  const [taskStats, setTaskStats] = useState<any>(null);
  
  const [form] = Form.useForm();

  // 加载数据
  const loadData = async () => {
    try {
      const [groupsData, rulesData, tasksData, statsData] = await Promise.all([
        telegramApi.getAllGroups(),
        ruleApi.getRules(0, 50),
        taskApi.getTasks({ limit: 5 }),
        taskApi.getTaskStats()
      ]);
      
      setGroups(groupsData);
      setRules(rulesData);
      setRecentTasks(tasksData);
      setTaskStats(statsData);
    } catch (error: any) {
      message.error(`加载数据失败: ${error.message}`);
    }
  };

  // 快速创建并执行任务
  const handleQuickExecute = async (values: any) => {
    try {
      setLoading(true);
      
      // 生成默认任务名称
      const group = groups.find(g => g.id === values.group_id);
      const selectedRules = rules.filter(r => values.rule_ids.includes(r.id));
      const rulesNames = selectedRules.map(r => r.name).join('_');
      const taskName = values.name || `${group?.title || 'Group'}_${rulesNames || 'Rules'}_${Date.now()}`;
      
      // 创建任务
      const task = await taskApi.createTask({
        name: taskName,
        group_id: values.group_id,
        rule_ids: values.rule_ids,
        download_path: values.download_path || `/downloads/${taskName.replace(/[^a-zA-Z0-9]/g, '_')}`
      });

      // 立即启动任务
      await taskApi.startTask(task.id);
      
      message.success('任务创建并启动成功！');
      setQuickExecuteVisible(false);
      form.resetFields();
      loadData();
      
      if (onTaskCreated) {
        onTaskCreated(task);
      }
    } catch (error: any) {
      message.error(`快速执行失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 立即执行现有待执行任务
  const handleExecuteExistingTask = async (taskId: number) => {
    try {
      await taskApi.startTask(taskId);
      message.success('任务启动成功');
      loadData();
    } catch (error: any) {
      message.error(`启动任务失败: ${error.message}`);
    }
  };

  useEffect(() => {
    loadData();
    // 定时刷新任务状态
    const interval = setInterval(loadData, 30000); // 30秒刷新一次
    return () => clearInterval(interval);
  }, []);

  // 获取任务状态颜色
  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'orange',
      running: 'blue',
      completed: 'green',
      failed: 'red',
      paused: 'warning'
    };
    return colorMap[status] || 'default';
  };

  // 获取任务状态图标（当前未使用，保留以备后用）
  // const getStatusIcon = (status: string) => {
  //   const iconMap: Record<string, React.ReactNode> = {
  //     pending: <ClockCircleOutlined />,
  //     running: <PlayCircleOutlined spin />,
  //     completed: <CheckCircleOutlined />,
  //     failed: <ExclamationCircleOutlined />,
  //     paused: <PlayCircleOutlined />
  //   };
  //   return iconMap[status] || <ClockCircleOutlined />;
  // };

  return (
    <div>
      {/* 主控制面板 */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <RocketOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            <span>快速任务执行</span>
          </div>
        }
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setQuickExecuteVisible(true)}
          >
            创建执行
          </Button>
        }
        size="small"
      >
        {/* 任务状态统计 */}
        {taskStats && (
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: '#52c41a' }}>
                  {taskStats.running}
                </div>
                <div style={{ fontSize: 12, color: '#666' }}>运行中</div>
              </div>
            </Col>
            <Col xs={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: '#fa8c16' }}>
                  {taskStats.pending}
                </div>
                <div style={{ fontSize: 12, color: '#666' }}>待执行</div>
              </div>
            </Col>
            <Col xs={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: '#1890ff' }}>
                  {taskStats.completed}
                </div>
                <div style={{ fontSize: 12, color: '#666' }}>已完成</div>
              </div>
            </Col>
            <Col xs={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: '#f5222d' }}>
                  {taskStats.failed}
                </div>
                <div style={{ fontSize: 12, color: '#666' }}>失败</div>
              </div>
            </Col>
          </Row>
        )}

        {/* 最近任务列表 */}
        <div>
          <Text strong style={{ marginBottom: 8, display: 'block' }}>
            最近任务 ({recentTasks.length})
          </Text>
          {recentTasks.length > 0 ? (
            <List
              size="small"
              dataSource={recentTasks}
              renderItem={(task) => (
                <List.Item
                  style={{ padding: '8px 0' }}
                  actions={[
                    task.status === 'pending' && (
                      <Tooltip title="立即执行">
                        <Button
                          type="link"
                          size="small"
                          icon={<PlayCircleOutlined />}
                          onClick={() => handleExecuteExistingTask(task.id)}
                        >
                          执行
                        </Button>
                      </Tooltip>
                    )
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    title={
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Text ellipsis style={{ maxWidth: '200px' }}>{task.name}</Text>
                        <Badge
                          color={getStatusColor(task.status)}
                          text={task.status.toUpperCase()}
                        />
                      </div>
                    }
                    description={
                      <div style={{ fontSize: 12 }}>
                        <div>进度: {task.progress}%</div>
                        {task.progress > 0 && (
                          <Progress 
                            percent={task.progress} 
                            size="small" 
                            style={{ marginTop: 4 }}
                            showInfo={false}
                          />
                        )}
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: '20px 0', color: '#999' }}>
              暂无最近任务
            </div>
          )}
        </div>
      </Card>

      {/* 快速执行模态框 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <RocketOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            快速创建并执行任务
          </div>
        }
        open={quickExecuteVisible}
        onCancel={() => {
          setQuickExecuteVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Alert
          message="快速执行"
          description="创建任务后将立即开始执行下载"
          type="info"
          style={{ marginBottom: 16 }}
          showIcon
        />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleQuickExecute}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="group_id"
                label="目标群组"
                rules={[{ required: true, message: '请选择群组' }]}
              >
                <Select 
                  placeholder="选择群组"
                  showSearch
                  filterOption={(input, option) =>
                    String(option?.children || '').toLowerCase().indexOf(input.toLowerCase()) >= 0
                  }
                >
                  {groups.map(group => (
                    <Option key={group.id} value={group.id}>
                      {group.title}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="rule_ids"
                label="过滤规则"
                rules={[{ required: true, message: '请选择至少一个规则' }]}
              >
                <Select 
                  mode="multiple"
                  placeholder="选择规则（可多选）"
                  showSearch
                  filterOption={(input, option) =>
                    String(option?.children || '').toLowerCase().indexOf(input.toLowerCase()) >= 0
                  }
                >
                  {rules.map(rule => (
                    <Option key={rule.id} value={rule.id}>
                      {rule.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            name="name"
            label="任务名称（可选）"
            extra="留空将自动生成任务名称"
          >
            <Input placeholder="输入自定义任务名称" />
          </Form.Item>
          
          <Form.Item
            name="download_path"
            label="下载路径（可选）"
            extra="留空将自动生成下载路径"
          >
            <Input placeholder="如: /downloads/my_task" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={loading}
                icon={<RocketOutlined />}
              >
                立即创建并执行
              </Button>
              <Button 
                onClick={() => {
                  setQuickExecuteVisible(false);
                  form.resetFields();
                }}
              >
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default QuickTaskExecutor;