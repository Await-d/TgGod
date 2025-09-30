import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { UserOutlined, LockOutlined, EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store';
import { authApi } from '../services/apiService';
import { LoginRequest } from '../types';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setUser, setToken, setIsLoading } = useAuthStore();

  // 处理登录
  const handleLogin = async (values: LoginRequest) => {
    setLoading(true);
    setIsLoading(true);
    
    try {
      // 登录
      const loginResponse = await authApi.login(values);
      setToken(loginResponse.access_token);
      
      // 获取用户信息
      const userInfo = await authApi.getCurrentUser();
      setUser(userInfo);
      
      message.success('登录成功！');
      navigate('/dashboard');
      
    } catch (error: any) {
      console.error('登录失败:', error);
      message.error(error.message || '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
      setIsLoading(false);
    }
  };



  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <Card 
        style={{ 
          width: 400, 
          boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
          borderRadius: 12
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={2} style={{ color: '#1890ff', marginBottom: 8 }}>
            TgGod 管理系统
          </Title>
          <Text type="secondary">
            Telegram 群组消息管理平台
          </Text>
        </div>

        <Form
          form={form}
          name="login"
          onFinish={handleLogin}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[
              { required: true, message: '请输入用户名!' },
              { min: 3, message: '用户名至少3个字符!' }
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码!' },
              { min: 6, message: '密码至少6个字符!' }
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              autoComplete="current-password"
              iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
            />
          </Form.Item>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              block
              style={{ height: 44 }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', marginTop: 24, color: '#8c8c8c' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            © 2025 TgGod. 群组消息管理系统
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;