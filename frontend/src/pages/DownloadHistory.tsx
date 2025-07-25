import React, { useState, useEffect } from 'react';
import { downloadHistoryApi } from '../services/apiService';
import {
  Table,
  Card,
  Space,
  Button,
  Input,
  Select,
  DatePicker,
  Statistic,
  Row,
  Col,
  Tag,
  Modal,
  message,
  Tooltip,
  Popconfirm,
  Progress,
  Typography,
  Descriptions,
  Divider,
  Alert
} from 'antd';
import {
  DownloadOutlined,
  FileOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  FolderOpenOutlined,
  FilterOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';

import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Search } = Input;
const { Title, Text } = Typography;

interface DownloadRecord {
  id: number;
  task_id: number;
  task_name: string;
  group_name: string;
  file_name: string;
  local_file_path: string;
  file_size: number;
  file_type: string;
  message_id: number;
  sender_id: number;
  sender_name: string;
  message_date: string;
  message_text: string;
  download_status: string;
  download_progress: number;
  error_message?: string;
  download_started_at: string;
  download_completed_at: string;
}

interface DownloadHistoryStats {
  total_downloads: number;
  successful_downloads: number;
  failed_downloads: number;
  success_rate: number;
  total_file_size: number;
  file_types: Record<string, number>;
  top_tasks: Array<{ task_name: string; download_count: number }>;
  period_days: number;
}

interface FilterOptions {
  task_id?: number;
  group_id?: number;
  file_type?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}

// 启用dayjs相对时间插件
dayjs.extend(relativeTime);

const DownloadHistory: React.FC = () => {
  const [records, setRecords] = useState<DownloadRecord[]>([]);
  const [stats, setStats] = useState<DownloadHistoryStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<DownloadRecord | null>(null);
  const [statsModalVisible, setStatsModalVisible] = useState(false);
  
  // 过滤条件
  const [filters, setFilters] = useState<FilterOptions>({});
  const [searchText, setSearchText] = useState('');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  
  // 分页
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 20,
    total: 0,
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
  });

  // 加载下载记录
  const loadDownloadRecords = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: pageSize,
        ...filters,
        ...(searchText && { search: searchText }),
        ...(dateRange && {
          date_from: dateRange[0].toISOString(),
          date_to: dateRange[1].toISOString(),
        }),
      };

      const data = await downloadHistoryApi.getDownloadRecords(params);
      setRecords(data.records);
      setPagination(prev => ({
        ...prev,
        current: data.page,
        total: data.total,
        pageSize: data.page_size,
      }));
    } catch (error) {
      console.error('Error loading download records:', error);
      message.error('加载下载历史失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载统计信息
  const loadStats = async (days = 30) => {
    try {
      const data = await downloadHistoryApi.getDownloadStats(days);
      setStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
      message.error('加载统计信息失败');
    }
  };

  // 删除记录
  const handleDelete = async (recordId: number) => {
    try {
      await downloadHistoryApi.deleteDownloadRecord(recordId);
      message.success('删除成功');
      loadDownloadRecords(pagination.current, pagination.pageSize);
    } catch (error) {
      console.error('Error deleting record:', error);
      message.error('删除失败');
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的记录');
      return;
    }

    try {
      const result = await downloadHistoryApi.batchDeleteRecords(selectedRowKeys as number[]);
      message.success(`成功删除 ${result.deleted_count} 条记录`);
      setSelectedRowKeys([]);
      loadDownloadRecords(pagination.current, pagination.pageSize);
    } catch (error) {
      console.error('Error batch deleting records:', error);
      message.error('批量删除失败');
    }
  };

  // 查看记录详情
  const handleViewDetail = (record: DownloadRecord) => {
    setSelectedRecord(record);
    setDetailModalVisible(true);
  };

  // 打开文件所在文件夹
  const handleOpenFolder = (filePath: string) => {
    // 这里可以实现打开文件夹的逻辑
    message.info('打开文件夹功能需要与系统集成实现');
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 获取文件类型标签颜色
  const getFileTypeColor = (fileType: string): string => {
    const colors: Record<string, string> = {
      photo: 'green',
      video: 'blue',
      document: 'orange',
      audio: 'purple',
      animation: 'cyan',
    };
    return colors[fileType] || 'default';
  };

  // 获取下载状态标签
  const getStatusTag = (status: string, progress: number) => {
    switch (status) {
      case 'completed':
        return <Tag color="success">已完成</Tag>;
      case 'failed':
        return <Tag color="error">失败</Tag>;
      case 'partial':
        return (
          <Tooltip title={`进度: ${progress}%`}>
            <Tag color="warning">部分完成</Tag>
          </Tooltip>
        );
      default:
        return <Tag color="default">{status}</Tag>;
    }
  };

  // 表格列定义
  const columns: ColumnsType<DownloadRecord> = [
    {
      title: '文件名',
      dataIndex: 'file_name',
      key: 'file_name',
      ellipsis: {
        showTitle: false,
      },
      render: (text: string, record: DownloadRecord) => (
        <Tooltip title={text}>
          <Space>
            <FileOutlined />
            <Text strong>{text}</Text>
          </Space>
        </Tooltip>
      ),
    },
    {
      title: '任务',
      dataIndex: 'task_name',
      key: 'task_name',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: '群组',
      dataIndex: 'group_name',
      key: 'group_name',
      ellipsis: true,
    },
    {
      title: '文件类型',
      dataIndex: 'file_type',
      key: 'file_type',
      render: (fileType: string) => (
        <Tag color={getFileTypeColor(fileType)}>
          {fileType?.toUpperCase() || '未知'}
        </Tag>
      ),
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => size ? formatFileSize(size) : '未知',
      sorter: true,
    },
    {
      title: '发送者',
      dataIndex: 'sender_name',
      key: 'sender_name',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'download_status',
      key: 'download_status',
      render: (status: string, record: DownloadRecord) => 
        getStatusTag(status, record.download_progress),
    },
    {
      title: '下载时间',
      dataIndex: 'download_completed_at',
      key: 'download_completed_at',
      render: (date: string) => (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          {dayjs(date).fromNow()}
        </Tooltip>
      ),
      sorter: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record: DownloadRecord) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Tooltip title="打开文件夹">
            <Button
              type="text"
              icon={<FolderOpenOutlined />}
              onClick={() => handleOpenFolder(record.local_file_path)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这条记录吗？"
            description="删除后无法恢复，但不会删除本地文件"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 行选择配置
  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
  };

  // 处理表格变化
  const handleTableChange = (paginationConfig: TablePaginationConfig) => {
    loadDownloadRecords(paginationConfig.current, paginationConfig.pageSize);
  };

  // 应用过滤器
  const handleApplyFilters = () => {
    loadDownloadRecords(1, pagination.pageSize);
  };

  // 重置过滤器
  const handleResetFilters = () => {
    setFilters({});
    setSearchText('');
    setDateRange(null);
    setPagination(prev => ({ ...prev, current: 1 }));
    setTimeout(() => {
      loadDownloadRecords(1, pagination.pageSize);
    }, 100);
  };

  // 初始化数据
  useEffect(() => {
    loadDownloadRecords();
    loadStats();
  }, []);

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <DownloadOutlined /> 下载历史
      </Title>
      
      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总下载数"
                value={stats.total_downloads}
                prefix={<DownloadOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="成功率"
                value={stats.success_rate}
                suffix="%"
                precision={1}
                valueStyle={{ 
                  color: stats.success_rate > 90 ? '#3f8600' : '#cf1322' 
                }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="总文件大小"
                value={formatFileSize(stats.total_file_size)}
                prefix={<FileOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="失败数量"
                value={stats.failed_downloads}
                valueStyle={{ color: stats.failed_downloads > 0 ? '#cf1322' : '#3f8600' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 过滤器和操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={6}>
            <Search
              placeholder="搜索文件名、发送者..."
              allowClear
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={handleApplyFilters}
              enterButton={<SearchOutlined />}
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder="文件类型"
              allowClear
              style={{ width: '100%' }}
              value={filters.file_type}
              onChange={(value) => setFilters(prev => ({ ...prev, file_type: value }))}
            >
              <Option value="photo">图片</Option>
              <Option value="video">视频</Option>
              <Option value="document">文档</Option>
              <Option value="audio">音频</Option>
              <Option value="animation">动画</Option>
            </Select>
          </Col>
          <Col span={4}>
            <Select
              placeholder="下载状态"
              allowClear
              style={{ width: '100%' }}
              value={filters.status}
              onChange={(value) => setFilters(prev => ({ ...prev, status: value }))}
            >
              <Option value="completed">已完成</Option>
              <Option value="failed">失败</Option>
              <Option value="partial">部分完成</Option>
            </Select>
          </Col>
          <Col span={6}>
            <RangePicker
              style={{ width: '100%' }}
              value={dateRange}
              onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
              placeholder={['开始日期', '结束日期']}
            />
          </Col>
          <Col span={4}>
            <Space>
              <Button
                type="primary"
                icon={<FilterOutlined />}
                onClick={handleApplyFilters}
              >
                筛选
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleResetFilters}
              >
                重置
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Popconfirm
                title={`确定要删除选中的 ${selectedRowKeys.length} 条记录吗？`}
                description="删除后无法恢复，但不会删除本地文件"
                onConfirm={handleBatchDelete}
                disabled={selectedRowKeys.length === 0}
                okText="确定"
                cancelText="取消"
              >
                <Button
                  danger
                  icon={<DeleteOutlined />}
                  disabled={selectedRowKeys.length === 0}
                >
                  批量删除 ({selectedRowKeys.length})
                </Button>
              </Popconfirm>
              <Button
                icon={<BarChartOutlined />}
                onClick={() => setStatsModalVisible(true)}
              >
                查看统计
              </Button>
            </Space>
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => loadDownloadRecords(pagination.current, pagination.pageSize)}
              loading={loading}
            >
              刷新
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 下载记录表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={loading}
          pagination={pagination}
          rowSelection={rowSelection}
          onChange={handleTableChange}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 记录详情弹窗 */}
      <Modal
        title="下载记录详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedRecord && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="文件名" span={2}>
                {selectedRecord.file_name}
              </Descriptions.Item>
              <Descriptions.Item label="任务名称">
                {selectedRecord.task_name}
              </Descriptions.Item>
              <Descriptions.Item label="群组名称">
                {selectedRecord.group_name}
              </Descriptions.Item>
              <Descriptions.Item label="文件类型">
                <Tag color={getFileTypeColor(selectedRecord.file_type)}>
                  {selectedRecord.file_type?.toUpperCase() || '未知'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="文件大小">
                {selectedRecord.file_size ? formatFileSize(selectedRecord.file_size) : '未知'}
              </Descriptions.Item>
              <Descriptions.Item label="发送者">
                {selectedRecord.sender_name}
              </Descriptions.Item>
              <Descriptions.Item label="消息ID">
                {selectedRecord.message_id}
              </Descriptions.Item>
              <Descriptions.Item label="下载状态">
                {getStatusTag(selectedRecord.download_status, selectedRecord.download_progress)}
              </Descriptions.Item>
              <Descriptions.Item label="下载进度">
                <Progress percent={selectedRecord.download_progress} size="small" />
              </Descriptions.Item>
              <Descriptions.Item label="本地路径" span={2}>
                <Text code copyable>{selectedRecord.local_file_path}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="消息时间">
                {selectedRecord.message_date && 
                  dayjs(selectedRecord.message_date).format('YYYY-MM-DD HH:mm:ss')
                }
              </Descriptions.Item>
              <Descriptions.Item label="下载完成时间">
                {dayjs(selectedRecord.download_completed_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>
            
            {selectedRecord.message_text && (
              <>
                <Divider>消息内容</Divider>
                <Alert
                  message={selectedRecord.message_text}
                  type="info"
                  style={{ wordBreak: 'break-word' }}
                />
              </>
            )}
            
            {selectedRecord.error_message && (
              <>
                <Divider>错误信息</Divider>
                <Alert
                  message={selectedRecord.error_message}
                  type="error"
                  style={{ wordBreak: 'break-word' }}
                />
              </>
            )}
          </div>
        )}
      </Modal>

      {/* 统计信息弹窗 */}
      <Modal
        title="下载统计信息"
        open={statsModalVisible}
        onCancel={() => setStatsModalVisible(false)}
        footer={null}
        width={600}
      >
        {stats && (
          <div>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic title="总下载数" value={stats.total_downloads} />
              </Col>
              <Col span={12}>
                <Statistic title="成功率" value={stats.success_rate} suffix="%" precision={1} />
              </Col>
            </Row>
            <Divider>文件类型分布</Divider>
            <div>
              {Object.entries(stats.file_types).map(([type, count]) => (
                <div key={type} style={{ marginBottom: 8 }}>
                  <Tag color={getFileTypeColor(type)}>{type.toUpperCase()}</Tag>
                  <span style={{ marginLeft: 8 }}>{count} 个文件</span>
                </div>
              ))}
            </div>
            <Divider>热门任务</Divider>
            <div>
              {stats.top_tasks.map((task, index) => (
                <div key={index} style={{ marginBottom: 8 }}>
                  <Text strong>{task.task_name}</Text>
                  <span style={{ marginLeft: 8, color: '#666' }}>
                    {task.download_count} 次下载
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default DownloadHistory;