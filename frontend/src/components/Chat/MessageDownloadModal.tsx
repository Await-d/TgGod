import React, { useState, useEffect } from 'react';
import { 
  Modal, 
  Form, 
  Input, 
  Select, 
  Button, 
  Space, 
  Card,
  Typography,
  Row,
  Col,
  message,
  Divider,
  InputNumber,
  DatePicker,
  Switch,
  Steps,
  Progress,
  List,
  Tag
} from 'antd';
import { 
  DownloadOutlined, 
  FolderOutlined, 
  FileTextOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { TelegramGroup, FilterRule, DownloadTask } from '../../types';
import { ruleApi, downloadApi } from '../../services/apiService';

const { Option } = Select;
const { Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Step } = Steps;

interface MessageDownloadModalProps {
  visible: boolean;
  onClose: () => void;
  selectedGroup: TelegramGroup | null;
  onSuccess?: (task: DownloadTask) => void;
  isMobile?: boolean;
}

const MessageDownloadModal: React.FC<MessageDownloadModalProps> = ({
  visible,
  onClose,
  selectedGroup,
  onSuccess,
  isMobile = false
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [availableRules, setAvailableRules] = useState<FilterRule[]>([]);
  const [selectedRule, setSelectedRule] = useState<FilterRule | null>(null);
  const [downloadPath, setDownloadPath] = useState('');
  const [estimatedCount, setEstimatedCount] = useState(0);
  const [createdTask, setCreatedTask] = useState<DownloadTask | null>(null);

  // 获取可用规则
  const fetchAvailableRules = async () => {
    if (!selectedGroup) return;
    
    try {
      const rules = await ruleApi.getGroupRules(selectedGroup.id);
      setAvailableRules(rules.filter(rule => rule.is_active));
    } catch (error: any) {
      message.error('获取规则失败: ' + error.message);
    }
  };

  // 预估下载数量
  const estimateDownloadCount = async (ruleId: number) => {
    if (!selectedGroup) return;
    
    try {
      const count = await downloadApi.estimateDownloadCount(selectedGroup.id, ruleId);
      setEstimatedCount(count);
    } catch (error: any) {
      console.error('预估下载数量失败:', error);
      setEstimatedCount(0);
    }
  };

  // 创建下载任务
  const handleCreateDownload = async (values: any) => {
    if (!selectedGroup || !selectedRule) return;
    
    setLoading(true);
    try {
      const taskData = {
        name: values.name || `${selectedGroup.title} - ${selectedRule.name}`,
        group_id: selectedGroup.id,
        rule_id: selectedRule.id,
        download_path: values.download_path || downloadPath,
        start_immediately: values.start_immediately !== false,
      };
      
      const task = await downloadApi.createDownloadTask(taskData);
      setCreatedTask(task);
      setCurrentStep(2);
      
      message.success('下载任务创建成功！');
      
      // 延迟调用成功回调
      setTimeout(() => {
        onSuccess?.(task);
        onClose();
      }, 2000);
    } catch (error: any) {
      message.error('创建下载任务失败: ' + error.message);
      console.error('创建下载任务失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 处理规则选择
  const handleRuleSelect = (ruleId: number) => {
    const rule = availableRules.find(r => r.id === ruleId);
    if (rule) {
      setSelectedRule(rule);
      estimateDownloadCount(ruleId);
      setCurrentStep(1);
    }
  };

  // 处理下一步
  const handleNext = () => {
    if (currentStep === 1) {
      form.submit();
    }
  };

  // 处理上一步
  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  // 处理取消
  const handleCancel = () => {
    onClose();
    setCurrentStep(0);
    setSelectedRule(null);
    setEstimatedCount(0);
    setCreatedTask(null);
    form.resetFields();
  };

  // 生成默认下载路径
  const generateDownloadPath = () => {
    if (selectedGroup && selectedRule) {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const path = `/downloads/${selectedGroup.title}/${selectedRule.name}_${timestamp}`;
      setDownloadPath(path);
      form.setFieldsValue({ download_path: path });
    }
  };

  // 当模态框打开时初始化
  useEffect(() => {
    if (visible) {
      fetchAvailableRules();
      generateDownloadPath();
    }
  }, [visible, selectedGroup]);

  // 渲染步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>选择下载规则</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                请选择一个已配置的规则来下载消息
              </Text>
            </div>
            
            {availableRules.length > 0 ? (
              <List
                dataSource={availableRules}
                renderItem={(rule) => (
                  <List.Item
                    style={{ cursor: 'pointer' }}
                    onClick={() => handleRuleSelect(rule.id)}
                  >
                    <Card 
                      size="small" 
                      style={{ width: '100%' }}
                      hoverable
                      bodyStyle={{ padding: '12px 16px' }}
                    >
                      <Row align="middle">
                        <Col flex="auto">
                          <div style={{ marginBottom: 4 }}>
                            <Text strong>{rule.name}</Text>
                            <Tag 
                              color={rule.is_active ? 'green' : 'default'}
                              style={{ marginLeft: 8 }}
                            >
                              {rule.is_active ? '启用' : '禁用'}
                            </Tag>
                          </div>
                          
                          <div style={{ marginBottom: 4 }}>
                            <Space size="small" wrap>
                              {rule.keywords.length > 0 && (
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  关键词: {rule.keywords.join(', ')}
                                </Text>
                              )}
                              {rule.media_types.length > 0 && (
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  媒体: {rule.media_types.join(', ')}
                                </Text>
                              )}
                            </Space>
                          </div>
                          
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            创建时间: {new Date(rule.created_at).toLocaleString('zh-CN')}
                          </Text>
                        </Col>
                        
                        <Col>
                          <Button type="primary" size="small">
                            选择
                          </Button>
                        </Col>
                      </Row>
                    </Card>
                  </List.Item>
                )}
              />
            ) : (
              <Card>
                <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                  <FileTextOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                  <div style={{ marginTop: 16 }}>
                    <Text type="secondary">
                      没有可用的下载规则，请先创建规则
                    </Text>
                  </div>
                </div>
              </Card>
            )}
          </div>
        );
        
      case 1:
        return (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>配置下载任务</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                设置下载任务的详细参数
              </Text>
            </div>
            
            {/* 选中规则信息 */}
            {selectedRule && (
              <Card size="small" style={{ marginBottom: 16, backgroundColor: '#f5f5f5' }}>
                <div style={{ marginBottom: 8 }}>
                  <Text strong>选中规则: </Text>
                  <Text>{selectedRule.name}</Text>
                </div>
                
                <div style={{ marginBottom: 8 }}>
                  <Text strong>预估消息数量: </Text>
                  <Text type="secondary">{estimatedCount.toLocaleString()} 条</Text>
                </div>
                
                {selectedRule.keywords.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <Text strong>关键词: </Text>
                    <Text type="secondary">{selectedRule.keywords.join(', ')}</Text>
                  </div>
                )}
                
                {selectedRule.media_types.length > 0 && (
                  <div>
                    <Text strong>媒体类型: </Text>
                    <Text type="secondary">{selectedRule.media_types.join(', ')}</Text>
                  </div>
                )}
              </Card>
            )}
            
            <Form
              form={form}
              layout="vertical"
              onFinish={handleCreateDownload}
              initialValues={{
                download_path: downloadPath,
                start_immediately: true,
              }}
            >
              <Form.Item
                name="name"
                label="任务名称"
                rules={[{ required: true, message: '请输入任务名称' }]}
              >
                <Input 
                  placeholder="请输入任务名称"
                  maxLength={100}
                />
              </Form.Item>
              
              <Form.Item
                name="download_path"
                label="下载路径"
                rules={[{ required: true, message: '请输入下载路径' }]}
              >
                <Input 
                  placeholder="请输入下载路径"
                  addonBefore={<FolderOutlined />}
                />
              </Form.Item>
              
              <Form.Item
                name="start_immediately"
                label="立即开始"
                valuePropName="checked"
              >
                <Switch />
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  创建后立即开始下载
                </Text>
              </Form.Item>
            </Form>
          </div>
        );
        
      case 2:
        return (
          <div>
            <div style={{ textAlign: 'center', padding: '40px 20px' }}>
              <CheckCircleOutlined 
                style={{ fontSize: 64, color: '#52c41a' }}
              />
              
              <div style={{ marginTop: 24 }}>
                <Text strong style={{ fontSize: 18 }}>
                  下载任务创建成功！
                </Text>
              </div>
              
              {createdTask && (
                <Card 
                  size="small" 
                  style={{ marginTop: 16, textAlign: 'left' }}
                >
                  <div style={{ marginBottom: 8 }}>
                    <Text strong>任务名称: </Text>
                    <Text>{createdTask.name}</Text>
                  </div>
                  
                  <div style={{ marginBottom: 8 }}>
                    <Text strong>下载路径: </Text>
                    <Text type="secondary">{createdTask.download_path}</Text>
                  </div>
                  
                  <div style={{ marginBottom: 8 }}>
                    <Text strong>任务状态: </Text>
                    <Tag color={createdTask.status === 'running' ? 'processing' : 'default'}>
                      {createdTask.status === 'running' ? '运行中' : '等待中'}
                    </Tag>
                  </div>
                  
                  <div>
                    <Text strong>创建时间: </Text>
                    <Text type="secondary">
                      {new Date(createdTask.created_at).toLocaleString('zh-CN')}
                    </Text>
                  </div>
                </Card>
              )}
              
              <div style={{ marginTop: 24 }}>
                <Text type="secondary">
                  你可以在下载任务页面查看进度
                </Text>
              </div>
            </div>
          </div>
        );
        
      default:
        return null;
    }
  };

  return (
    <Modal
      title={
        <Space>
          <DownloadOutlined />
          下载消息
          {selectedGroup && (
            <Text type="secondary">
              - {selectedGroup.title}
            </Text>
          )}
        </Space>
      }
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={isMobile ? '100%' : 700}
      style={isMobile ? { top: 20 } : {}}
      destroyOnClose
    >
      <div style={{ marginBottom: 24 }}>
        <Steps current={currentStep} size="small">
          <Step title="选择规则" />
          <Step title="配置参数" />
          <Step title="创建完成" />
        </Steps>
      </div>
      
      <div style={{ minHeight: 400 }}>
        {renderStepContent()}
      </div>
      
      <Divider />
      
      <div style={{ textAlign: 'right' }}>
        <Space>
          <Button onClick={handleCancel}>
            取消
          </Button>
          
          {currentStep > 0 && currentStep < 2 && (
            <Button onClick={handlePrev}>
              上一步
            </Button>
          )}
          
          {currentStep === 1 && (
            <Button 
              type="primary" 
              onClick={handleNext}
              loading={loading}
            >
              创建任务
            </Button>
          )}
          
          {currentStep === 2 && (
            <Button 
              type="primary" 
              onClick={handleCancel}
            >
              完成
            </Button>
          )}
        </Space>
      </div>
    </Modal>
  );
};

export default MessageDownloadModal;