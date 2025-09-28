import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Alert,
  Table,
  Tag,
  Space,
  Typography,
  Statistic,
  Spin,
  Modal,
  message,
  Descriptions,
  Collapse
} from 'antd';
import {
  DatabaseOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  ReloadOutlined,
  ToolOutlined,
  InfoCircleOutlined,
  BugOutlined
} from '@ant-design/icons';
import api from '../services/apiService';

const { Title, Text } = Typography;
const { Panel } = Collapse;

interface DatabaseHealth {
  status: 'healthy' | 'needs_repair' | 'error';
  issues_count: number;
  tables_count: number;
  last_check: string;
}

interface DatabaseInfo {
  database_url: string;
  table_count: number;
  tables: Record<string, {
    columns: string[];
    column_count: number;
    indexes: string[];
    index_count: number;
  }>;
}

interface CheckResult {
  missing_tables: string[];
  missing_columns: Record<string, string[]>;
  status: 'healthy' | 'needs_repair' | 'error';
  issues_found: number;
  fixed_issues: number;
  errors: string[];
}

const DatabaseStatus: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [checkLoading, setCheckLoading] = useState(false);
  const [repairLoading, setRepairLoading] = useState(false);
  const [health, setHealth] = useState<DatabaseHealth | null>(null);
  const [dbInfo, setDbInfo] = useState<DatabaseInfo | null>(null);
  const [checkResult, setCheckResult] = useState<CheckResult | null>(null);
  const [repairModalVisible, setRepairModalVisible] = useState(false);

  // 获取数据库健康状态
  const fetchDatabaseHealth = async () => {
    try {
      setLoading(true);
      const response = await api.get('/database/health');
      setHealth(response.data.data);
    } catch (error: any) {
      message.error(`获取数据库健康状态失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 获取数据库信息
  const fetchDatabaseInfo = async () => {
    try {
      const response = await api.get('/database/info');
      setDbInfo(response.data.data);
    } catch (error: any) {
      message.error(`获取数据库信息失败: ${error.message}`);
    }
  };

  // 检查数据库结构
  const checkDatabaseStructure = async () => {
    try {
      setCheckLoading(true);
      const response = await api.get('/database/check');
      setCheckResult(response.data.data);
      message.success(response.data.message || '数据库检查完成');
    } catch (error: any) {
      message.error(`数据库检查失败: ${error.message}`);
    } finally {
      setCheckLoading(false);
    }
  };

  // 修复数据库结构
  const repairDatabaseStructure = async () => {
    try {
      setRepairLoading(true);
      const response = await api.post('/database/repair');
      
      if (response.data.success) {
        message.success(response.data.message || '数据库修复完成');
        // 刷新数据
        await Promise.all([
          fetchDatabaseHealth(),
          checkDatabaseStructure()
        ]);
      } else {
        message.warning(response.data.message || '数据库修复失败');
      }
      
      setRepairModalVisible(false);
    } catch (error: any) {
      message.error(`数据库修复失败: ${error.message}`);
    } finally {
      setRepairLoading(false);
    }
  };

  // 运行启动检查
  const runStartupCheck = async () => {
    try {
      setLoading(true);
      const response = await api.post('/database/startup-check');
      
      if (response.data.success) {
        message.success('启动检查完成');
      } else {
        message.warning('启动检查发现问题');
      }
      
      // 刷新所有数据
      await Promise.all([
        fetchDatabaseHealth(),
        fetchDatabaseInfo(),
        checkDatabaseStructure()
      ]);
    } catch (error: any) {
      message.error(`启动检查失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 获取状态图标和颜色
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'needs_repair':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#f5222d' }} />;
      default:
        return <InfoCircleOutlined />;
    }
  };


  // 构建表格数据
  const getTableColumns = () => [
    {
      title: '表名',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <Text strong>{name}</Text>
    },
    {
      title: '字段数',
      dataIndex: 'column_count',
      key: 'column_count',
      align: 'center' as const
    },
    {
      title: '索引数',
      dataIndex: 'index_count',
      key: 'index_count',
      align: 'center' as const
    },
    {
      title: '状态',
      key: 'status',
      render: (record: any) => {
        const hasIssues = (checkResult?.missing_columns && checkResult.missing_columns[record.name]?.length > 0) || false;
        return (
          <Tag color={hasIssues ? 'orange' : 'green'}>
            {hasIssues ? '需要修复' : '正常'}
          </Tag>
        );
      }
    }
  ];

  const getTableData = () => {
    if (!dbInfo) return [];
    
    return Object.entries(dbInfo.tables).map(([name, info]) => ({
      key: name,
      name,
      column_count: info.column_count,
      index_count: info.index_count,
      columns: info.columns,
      indexes: info.indexes
    }));
  };

  // 初始化数据
  useEffect(() => {
    const initData = async () => {
      await Promise.all([
        fetchDatabaseHealth(),
        fetchDatabaseInfo(),
        checkDatabaseStructure()
      ]);
    };
    
    initData();
  }, []);

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <DatabaseOutlined style={{ marginRight: 8 }} />
        数据库状态监控
      </Title>

      {/* 概览卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="数据库状态"
              value={health?.status || '-'}
              prefix={health ? getStatusIcon(health.status) : <Spin size="small" />}
              valueStyle={{ 
                color: health ? (health.status === 'healthy' ? '#52c41a' : 
                                health.status === 'needs_repair' ? '#faad14' : '#f5222d') : undefined
              }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="表数量"
              value={health?.tables_count || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="发现问题"
              value={health?.issues_count || 0}
              prefix={<BugOutlined />}
              valueStyle={{ color: (health?.issues_count || 0) > 0 ? '#f5222d' : '#52c41a' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="最后检查"
              value={health?.last_check || '-'}
              prefix={<ReloadOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作按钮 */}
      <Card style={{ marginBottom: 24 }}>
        <Space>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            loading={loading}
            onClick={() => Promise.all([
              fetchDatabaseHealth(),
              fetchDatabaseInfo(),
              checkDatabaseStructure()
            ])}
          >
            刷新状态
          </Button>
          
          <Button
            icon={<BugOutlined />}
            loading={checkLoading}
            onClick={checkDatabaseStructure}
          >
            结构检查
          </Button>
          
          <Button
            icon={<ToolOutlined />}
            type="default"
            danger={checkResult?.status === 'needs_repair'}
            disabled={!checkResult || checkResult.status === 'healthy'}
            onClick={() => setRepairModalVisible(true)}
          >
            修复问题
          </Button>
          
          <Button
            icon={<DatabaseOutlined />}
            onClick={runStartupCheck}
            loading={loading}
          >
            启动检查
          </Button>
        </Space>
      </Card>

      {/* 检查结果 */}
      {checkResult && (
        <Card title="结构检查结果" style={{ marginBottom: 24 }}>
          <Alert
            message={`检查完成：发现 ${checkResult.issues_found} 个问题`}
            type={checkResult.status === 'healthy' ? 'success' : 
                  checkResult.status === 'needs_repair' ? 'warning' : 'error'}
            showIcon
            style={{ marginBottom: 16 }}
          />
          
          {checkResult.missing_tables.length > 0 && (
            <Alert
              message="缺失的表"
              description={
                <div>
                  {checkResult.missing_tables.map(table => (
                    <Tag key={table} color="red">{table}</Tag>
                  ))}
                </div>
              }
              type="error"
              style={{ marginBottom: 16 }}
            />
          )}
          
          {Object.keys(checkResult.missing_columns).length > 0 && (
            <Alert
              message="缺失的字段"
              description={
                <Collapse size="small">
                  {Object.entries(checkResult.missing_columns).map(([table, columns]) => (
                    <Panel header={`表: ${table}`} key={table}>
                      {columns.map(column => (
                        <Tag key={column} color="orange">{column}</Tag>
                      ))}
                    </Panel>
                  ))}
                </Collapse>
              }
              type="warning"
              style={{ marginBottom: 16 }}
            />
          )}
          
          {checkResult.errors.length > 0 && (
            <Alert
              message="检查错误"
              description={
                <ul>
                  {checkResult.errors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              }
              type="error"
            />
          )}
        </Card>
      )}

      {/* 数据库表信息 */}
      {dbInfo && (
        <Card title="数据库表信息">
          <Descriptions style={{ marginBottom: 16 }}>
            <Descriptions.Item label="数据库URL">
              {dbInfo.database_url}
            </Descriptions.Item>
            <Descriptions.Item label="表总数">
              {dbInfo.table_count}
            </Descriptions.Item>
          </Descriptions>
          
          <Table
            columns={getTableColumns()}
            dataSource={getTableData()}
            size="small"
            pagination={false}
            expandable={{
              expandedRowRender: (record) => (
                <div>
                  <Descriptions size="small" column={1}>
                    <Descriptions.Item label="字段列表">
                      <div>
                        {record.columns.map((column: string) => (
                          <Tag key={column} color="blue" style={{ margin: 2 }}>
                            {column}
                          </Tag>
                        ))}
                      </div>
                    </Descriptions.Item>
                    <Descriptions.Item label="索引列表">
                      <div>
                        {record.indexes.map((index: string) => (
                          <Tag key={index} color="green" style={{ margin: 2 }}>
                            {index}
                          </Tag>
                        ))}
                      </div>
                    </Descriptions.Item>
                  </Descriptions>
                </div>
              )
            }}
          />
        </Card>
      )}

      {/* 修复确认模态框 */}
      <Modal
        title="确认修复数据库结构"
        open={repairModalVisible}
        onOk={repairDatabaseStructure}
        onCancel={() => setRepairModalVisible(false)}
        confirmLoading={repairLoading}
        okText="开始修复"
        cancelText="取消"
      >
        <Alert
          message="修复警告"
          description={
            <div>
              <p>即将执行以下修复操作：</p>
              <ul>
                {checkResult?.missing_tables.map(table => (
                  <li key={table}>创建缺失的表: <Text code>{table}</Text></li>
                ))}
                {Object.entries(checkResult?.missing_columns || {}).map(([table, columns]) => (
                  <li key={table}>
                    为表 <Text code>{table}</Text> 添加字段: {columns.join(', ')}
                  </li>
                ))}
              </ul>
              <p><Text type="warning">⚠️ 请确保在修复前已备份重要数据</Text></p>
            </div>
          }
          type="warning"
          showIcon
        />
      </Modal>
    </div>
  );
};

export default DatabaseStatus;