import React from 'react';
import { 
  Table, 
  Button, 
  Space, 
  Modal, 
  Form, 
  Input, 
  message, 
  Popconfirm,
  Tag,
  Typography,
  Card,
  Statistic,
  Row,
  Col,
  Checkbox,
  Progress,
  Divider,
  Alert
} from 'antd';
import { 
  PlusOutlined, 
  SyncOutlined, 
  DeleteOutlined, 
  PlayCircleOutlined,
  PauseCircleOutlined,
  TeamOutlined,
  CloudSyncOutlined,
  CheckSquareOutlined,
  BorderOutlined
} from '@ant-design/icons';
import { TelegramGroup } from '../types';
import { useTelegramStore, useGlobalStore } from '../store';
import { telegramApi } from '../services/apiService';
import { useNormalPageScrollControl } from '../hooks/usePageScrollControl';

const { Title } = Typography;

const Groups: React.FC = () => {
  // 恢复正常页面滚动
  useNormalPageScrollControl();
  
  const { groups, setGroups, addGroup, updateGroup, removeGroup } = useTelegramStore();
  const { setLoading, setError } = useGlobalStore();
  const [isModalVisible, setIsModalVisible] = React.useState(false);
  const [isSyncModalVisible, setIsSyncModalVisible] = React.useState(false);
  const [form] = Form.useForm();
  const [syncForm] = Form.useForm();
  
  // 批量操作相关状态
  const [selectedRowKeys, setSelectedRowKeys] = React.useState<React.Key[]>([]);
  const [batchSyncing, setBatchSyncing] = React.useState(false);
  const [syncProgress, setSyncProgress] = React.useState<{
    current: number;
    total: number;
    currentGroup?: string;
    success: number;
    failed: number;
  }>({ current: 0, total: 0, success: 0, failed: 0 });
  const [showBatchProgress, setShowBatchProgress] = React.useState(false);

  const loadGroups = React.useCallback(async () => {
    setLoading(true);
    try {
      // 使用getAllGroups获取所有群组，避免分页限制
      const response = await telegramApi.getAllGroups();
      setGroups(response);
      console.log(`成功加载 ${response.length} 个群组`);
    } catch (error) {
      setError('加载群组列表失败');
      console.error('加载群组失败:', error);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setGroups]);

  React.useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  const handleAddGroup = async (values: { username: string }) => {
    try {
      const response = await telegramApi.addGroup(values.username);
      addGroup(response);
      setIsModalVisible(false);
      form.resetFields();
      message.success('群组添加成功');
    } catch (error) {
      message.error('添加群组失败');
      console.error('添加群组失败:', error);
    }
  };

  const handleSyncMessages = async (groupId: number) => {
    try {
      const response = await telegramApi.syncGroupMessages(groupId);
      message.success('消息同步成功');
    } catch (error) {
      message.error('消息同步失败');
      console.error('消息同步失败:', error);
    }
  };

  const handleToggleStatus = async (groupId: number, currentStatus: boolean) => {
    try {
      const response = await telegramApi.updateGroup(groupId, {
        is_active: !currentStatus
      });
      updateGroup(groupId, { is_active: !currentStatus });
      message.success('状态更新成功');
    } catch (error) {
      message.error('状态更新失败');
      console.error('状态更新失败:', error);
    }
  };

  const handleDeleteGroup = async (groupId: number) => {
    try {
      const response = await telegramApi.deleteGroup(groupId);
      removeGroup(groupId);
      message.success('群组删除成功');
    } catch (error) {
      message.error('删除群组失败');
      console.error('删除群组失败:', error);
    }
  };

  // 打开批量同步模态框
  const handleOpenBatchSync = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要同步的群组');
      return;
    }
    setIsSyncModalVisible(true);
  };

  // 批量同步消息处理函数
  const handleBatchSync = async (values: { limit: number }) => {
    setIsSyncModalVisible(false);

    setBatchSyncing(true);
    setShowBatchProgress(true);
    
    const selectedGroups = groups.filter(group => selectedRowKeys.includes(group.id));
    const selectedGroupIds = selectedGroups.map(group => group.id);
    
    setSyncProgress({
      current: 0,
      total: selectedGroups.length,
      success: 0,
      failed: 0
    });

    try {
      // 使用后端批量同步API
      const response = await telegramApi.batchSyncGroupMessages(selectedGroupIds, values.limit);
      
      // 验证响应格式
      if (!response || !Array.isArray(response.results)) {
        throw new Error('服务器返回了无效的响应格式');
      }
      
      // 统计成功和失败的数量
      let successCount = 0;
      let failedCount = 0;
      
      response.results.forEach(result => {
        if (result.success) {
          successCount++;
        } else {
          failedCount++;
        }
      });
      
      setSyncProgress({
        current: selectedGroups.length,
        total: selectedGroups.length,
        success: successCount,
        failed: failedCount
      });
      
      // 显示结果
      if (failedCount === 0) {
        message.success(`批量同步完成！成功同步 ${successCount} 个群组`);
      } else {
        message.warning(`批量同步完成！成功: ${successCount}, 失败: ${failedCount}`);
      }
    } catch (error: any) {
      console.error('批量同步API调用失败:', error);
      message.error(`批量同步失败: ${error.response?.data?.detail || '请求处理过程中出现错误'}`);
      
      // 回退到逐个同步
      console.warn('批量API不可用，使用逐个同步:', error);
        
        let successCount = 0;
        let failedCount = 0;

        for (let i = 0; i < selectedGroups.length; i++) {
          const group = selectedGroups[i];
          setSyncProgress(prev => ({
            ...prev,
            current: i + 1,
            currentGroup: group.title
          }));

          try {
            await telegramApi.syncGroupMessages(group.id, values.limit);
            successCount++;
            setSyncProgress(prev => ({ ...prev, success: successCount }));
          } catch (error) {
            failedCount++;
            setSyncProgress(prev => ({ ...prev, failed: failedCount }));
            console.error(`同步群组 ${group.title} 失败:`, error);
          }
        }
        
        // 显示最终结果
        if (failedCount === 0) {
          message.success(`批量同步完成！成功同步 ${successCount} 个群组`);
        } else {
          message.warning(`批量同步完成！成功: ${successCount}, 失败: ${failedCount}`);
        }
    } finally {
      setBatchSyncing(false);
      
      // 清空选择
      setSelectedRowKeys([]);
      
      // 3秒后隐藏进度
      setTimeout(() => {
        setShowBatchProgress(false);
      }, 3000);
    }
  };

  // 批量选择/取消选择
  const handleSelectAll = () => {
    if (selectedRowKeys.length === groups.length) {
      setSelectedRowKeys([]);
    } else {
      setSelectedRowKeys(groups.map(group => group.id));
    }
  };

  // 选择活跃群组
  const handleSelectActive = () => {
    const activeGroups = groups.filter(group => group.is_active);
    setSelectedRowKeys(activeGroups.map(group => group.id));
  };

  // 清空选择
  const handleClearSelection = () => {
    setSelectedRowKeys([]);
  };

  // 表格行选择配置
  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
    onSelect: (record: TelegramGroup, selected: boolean) => {
      if (selected) {
        setSelectedRowKeys([...selectedRowKeys, record.id]);
      } else {
        setSelectedRowKeys(selectedRowKeys.filter(key => key !== record.id));
      }
    },
    onSelectAll: (selected: boolean, selectedRows: TelegramGroup[], changeRows: TelegramGroup[]) => {
      if (selected) {
        const newKeys = groups.map(group => group.id);
        setSelectedRowKeys(newKeys);
      } else {
        setSelectedRowKeys([]);
      }
    },
  };

  const columns = [
    {
      title: '群组名称',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: TelegramGroup) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            @{record.username}
          </div>
        </div>
      ),
    },
    {
      title: '成员数量',
      dataIndex: 'member_count',
      key: 'member_count',
      render: (count: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <TeamOutlined />
          <span>{count.toLocaleString()}</span>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? '活跃' : '暂停'}
        </Tag>
      ),
    },
    {
      title: '添加时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: TelegramGroup) => (
        <Space size="middle">
          <Button
            type="text"
            size="small"
            icon={<SyncOutlined />}
            onClick={() => handleSyncMessages(record.id)}
          >
            同步消息
          </Button>
          <Button
            type="text"
            size="small"
            icon={record.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => handleToggleStatus(record.id, record.is_active)}
          >
            {record.is_active ? '暂停' : '启用'}
          </Button>
          <Popconfirm
            title="确定要删除这个群组吗？"
            description="删除后所有相关数据都将被清除"
            onConfirm={() => handleDeleteGroup(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2}>群组管理</Title>
        <Space>
          <Button icon={<SyncOutlined />} onClick={loadGroups}>
            刷新
          </Button>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={() => setIsModalVisible(true)}
          >
            添加群组
          </Button>
        </Space>
      </div>

      {/* 批量操作工具栏 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Space>
              <Button 
                icon={selectedRowKeys.length === groups.length ? <CheckSquareOutlined /> : <BorderOutlined />}
                onClick={handleSelectAll}
              >
                {selectedRowKeys.length === groups.length ? '取消全选' : '全选'}
              </Button>
              <Button onClick={handleSelectActive}>
                选择活跃群组
              </Button>
              <Button onClick={handleClearSelection} disabled={selectedRowKeys.length === 0}>
                清空选择
              </Button>
              <Divider type="vertical" />
              <span style={{ color: '#666' }}>
                已选择 {selectedRowKeys.length} / {groups.length} 个群组
              </span>
            </Space>
          </div>
          <Space>
            <Button
              type="primary"
              icon={<CloudSyncOutlined />}
              loading={batchSyncing}
              disabled={selectedRowKeys.length === 0}
              onClick={handleOpenBatchSync}
            >
              批量同步消息
            </Button>
          </Space>
        </div>
      </Card>

      {/* 批量同步进度显示 */}
      {showBatchProgress && (
        <Card style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8 }}>
            <strong>批量同步进度</strong>
          </div>
          <Progress
            percent={syncProgress.total ? Math.round((syncProgress.current / syncProgress.total) * 100) : 0}
            status={batchSyncing ? 'active' : 'success'}
            format={() => `${syncProgress.current}/${syncProgress.total}`}
            style={{ marginBottom: 8 }}
          />
          <div style={{ fontSize: '12px', color: '#666' }}>
            {syncProgress.currentGroup && batchSyncing && (
              <div>正在同步: {syncProgress.currentGroup}</div>
            )}
            <div>成功: {syncProgress.success} | 失败: {syncProgress.failed}</div>
          </div>
        </Card>
      )}

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总群组数"
              value={groups.length}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="活跃群组"
              value={groups.filter(g => g.is_active).length}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总成员数"
              value={groups.reduce((sum, g) => sum + g.member_count, 0)}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 群组表格 */}
      <Table
        columns={columns}
        dataSource={groups}
        rowKey="id"
        rowSelection={rowSelection}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        }}
      />

      {/* 添加群组模态框 */}
      <Modal
        title="添加群组"
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleAddGroup}
        >
          <Form.Item
            label="群组用户名"
            name="username"
            rules={[
              { required: true, message: '请输入群组用户名' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' }
            ]}
          >
            <Input 
              placeholder="请输入群组用户名（不包含@）"
              prefix="@"
            />
          </Form.Item>
          
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setIsModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                添加
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 批量同步选项模态框 */}
      <Modal
        title="批量同步选项"
        open={isSyncModalVisible}
        onCancel={() => {
          setIsSyncModalVisible(false);
          syncForm.resetFields();
        }}
        footer={null}
        width={480}
      >
        <Alert
          message={`将同步 ${selectedRowKeys.length} 个群组的消息`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        
        <Form
          form={syncForm}
          layout="vertical"
          onFinish={handleBatchSync}
          initialValues={{ limit: 100 }}
        >
          <Form.Item
            label="每个群组同步消息数量"
            name="limit"
            rules={[
              { required: true, message: '请输入同步数量' },
              { type: 'number', min: 1, max: 1000, message: '同步数量必须在1-1000之间' }
            ]}
            help="建议值：100条（测试）、500条（日常）、1000条（完整同步）"
          >
            <Input 
              type="number"
              placeholder="输入要同步的消息数量"
              suffix="条消息"
            />
          </Form.Item>
          
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setIsSyncModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={batchSyncing}>
                开始同步
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Groups;