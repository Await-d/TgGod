import React, { useEffect, useState } from 'react';
import {
  Form,
  Input,
  Button,
  Card,
  Space,
  message,
  Avatar,
  Row,
  Col,
  Spin,
  Divider,
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  SaveOutlined,
  ReloadOutlined,
  CameraOutlined,
  IdcardOutlined,
  LockOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../../store';
import apiService from '../../services/apiService';

const { TextArea } = Input;

interface UserProfileFormData {
  full_name?: string;
  avatar_url?: string;
  bio?: string;
}

const UserProfileForm: React.FC = () => {
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const { user, setUser } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  // 加载当前用户信息
  useEffect(() => {
    const loadUserProfile = async () => {
      setLoading(true);
      try {
        const response = await apiService.get('/auth/me');
        const userData = response.data || response;
        setUser(userData);
        form.setFieldsValue({
          full_name: userData.full_name || '',
          avatar_url: userData.avatar_url || '',
          bio: userData.bio || '',
        });
      } catch (error) {
        console.error('加载用户信息失败:', error);
        messageApi.error('加载用户信息失败');
      } finally {
        setLoading(false);
      }
    };

    loadUserProfile();
  }, [form, setUser, messageApi]);

  // 保存用户信息
  const handleSave = async (values: UserProfileFormData) => {
    setSaving(true);
    try {
      const response = await apiService.put('/auth/me', values);
      const updatedUser = response.data || response;
      setUser(updatedUser);
      messageApi.success('个人信息已保存');
    } catch (error: any) {
      console.error('保存个人信息失败:', error);
      const errorMessage = error?.response?.data?.detail || '保存失败';
      messageApi.error(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  // 重置表单
  const handleReset = () => {
    form.setFieldsValue({
      full_name: user?.full_name || '',
      avatar_url: user?.avatar_url || '',
      bio: user?.bio || '',
    });
    messageApi.info('已重置为当前保存的信息');
  };

  // 修改密码
  const handleChangePassword = async (values: {
    old_password: string;
    new_password: string;
    confirm_password: string;
  }) => {
    setChangingPassword(true);
    try {
      await apiService.put('/auth/change-password', {
        old_password: values.old_password,
        new_password: values.new_password,
      });
      messageApi.success('密码修改成功');
      passwordForm.resetFields();
    } catch (error: any) {
      console.error('修改密码失败:', error);
      const errorMessage = error?.response?.data?.detail || '密码修改失败';
      messageApi.error(errorMessage);
    } finally {
      setChangingPassword(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="加载用户信息中...">
          <div style={{ height: 200 }} />
        </Spin>
      </div>
    );
  }

  return (
    <>
      {contextHolder}
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSave}
        disabled={saving}
      >
        <Card
          title={
            <>
              <IdcardOutlined /> 基本信息
            </>
          }
          style={{ marginBottom: 16 }}
        >
          <Row gutter={24}>
            <Col xs={24} sm={24} md={8} style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Avatar
                  size={120}
                  src={form.getFieldValue('avatar_url')}
                  icon={<UserOutlined />}
                  style={{ marginBottom: 16 }}
                />
                <Form.Item
                  name="avatar_url"
                  style={{ marginBottom: 0, width: '100%' }}
                >
                  <Input
                    placeholder="头像 URL"
                    prefix={<CameraOutlined />}
                    onChange={(e) => {
                      form.setFieldsValue({ avatar_url: e.target.value });
                    }}
                  />
                </Form.Item>
              </div>
            </Col>

            <Col xs={24} sm={24} md={16}>
              <Form.Item label="用户名" style={{ marginBottom: 16 }}>
                <Input
                  value={user?.username}
                  disabled
                  prefix={<UserOutlined />}
                  placeholder="用户名（不可修改）"
                />
              </Form.Item>

              <Form.Item label="邮箱" style={{ marginBottom: 16 }}>
                <Input
                  value={user?.email}
                  disabled
                  prefix={<MailOutlined />}
                  placeholder="邮箱（不可修改）"
                />
              </Form.Item>

              <Form.Item
                label="真实姓名"
                name="full_name"
                tooltip="可选填写您的真实姓名或昵称"
                style={{ marginBottom: 16 }}
              >
                <Input
                  placeholder="请输入您的真实姓名或昵称"
                  prefix={<UserOutlined />}
                  maxLength={100}
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="个人简介"
            name="bio"
            tooltip="简单介绍一下自己"
          >
            <TextArea
              rows={4}
              placeholder="请输入个人简介（选填）"
              maxLength={500}
              showCount
            />
          </Form.Item>
        </Card>

        <Card
          title={
            <>
              <IdcardOutlined /> 账户状态
            </>
          }
          style={{ marginBottom: 16 }}
        >
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <div>
                <strong>账户状态：</strong>
                <span style={{ color: user?.is_active ? '#52c41a' : '#ff4d4f', marginLeft: 8 }}>
                  {user?.is_active ? '激活' : '禁用'}
                </span>
              </div>
            </Col>
            <Col span={12}>
              <div>
                <strong>账户类型：</strong>
                <span style={{ marginLeft: 8 }}>
                  {user?.is_superuser ? '管理员' : '普通用户'}
                </span>
              </div>
            </Col>
            <Col span={12}>
              <div>
                <strong>邮箱验证：</strong>
                <span style={{ color: user?.is_verified ? '#52c41a' : '#faad14', marginLeft: 8 }}>
                  {user?.is_verified ? '已验证' : '未验证'}
                </span>
              </div>
            </Col>
            <Col span={12}>
              <div>
                <strong>注册时间：</strong>
                <span style={{ marginLeft: 8 }}>
                  {user?.created_at ? new Date(user.created_at).toLocaleString('zh-CN') : '-'}
                </span>
              </div>
            </Col>
            <Col span={12}>
              <div>
                <strong>最后登录：</strong>
                <span style={{ marginLeft: 8 }}>
                  {user?.last_login ? new Date(user.last_login).toLocaleString('zh-CN') : '从未登录'}
                </span>
              </div>
            </Col>
          </Row>
        </Card>

        <Divider />

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={saving}
            >
              保存修改
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              disabled={saving}
            >
              重置
            </Button>
          </Space>
        </div>
      </Form>

      <Divider style={{ marginTop: 32, marginBottom: 24 }} />

      <Form
        form={passwordForm}
        layout="vertical"
        onFinish={handleChangePassword}
        disabled={changingPassword}
      >
        <Card
          title={
            <>
              <SafetyOutlined /> 安全设置
            </>
          }
          style={{ marginBottom: 16 }}
        >
          <Row gutter={24}>
            <Col xs={24} sm={24} md={12}>
              <Form.Item
                label="当前密码"
                name="old_password"
                rules={[
                  { required: true, message: '请输入当前密码' },
                ]}
              >
                <Input.Password
                  placeholder="请输入当前密码"
                  prefix={<LockOutlined />}
                  autoComplete="current-password"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col xs={24} sm={24} md={12}>
              <Form.Item
                label="新密码"
                name="new_password"
                rules={[
                  { required: true, message: '请输入新密码' },
                  { min: 6, message: '密码长度不能少于6个字符' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('old_password') !== value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('新密码不能与当前密码相同'));
                    },
                  }),
                ]}
              >
                <Input.Password
                  placeholder="请输入新密码（至少6个字符）"
                  prefix={<LockOutlined />}
                  autoComplete="new-password"
                />
              </Form.Item>
            </Col>

            <Col xs={24} sm={24} md={12}>
              <Form.Item
                label="确认新密码"
                name="confirm_password"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: '请确认新密码' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('两次输入的密码不一致'));
                    },
                  }),
                ]}
              >
                <Input.Password
                  placeholder="请再次输入新密码"
                  prefix={<LockOutlined />}
                  autoComplete="new-password"
                />
              </Form.Item>
            </Col>
          </Row>

          <div style={{ marginTop: 16 }}>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<LockOutlined />}
                loading={changingPassword}
                danger
              >
                修改密码
              </Button>
              <Button
                onClick={() => passwordForm.resetFields()}
                disabled={changingPassword}
              >
                清空
              </Button>
            </Space>
          </div>
        </Card>
      </Form>
    </>
  );
};

export default UserProfileForm;