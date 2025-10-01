import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { UserOutlined, LockOutlined, EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store';
import { authApi } from '../services/apiService';
import { LoginRequest } from '../types';
import './Login.css';

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
    <div className="login-page">
      <Card className="login-card">
        <div className="login-header">
          <Title level={2} className="login-title">
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
              className="login-submit"
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div className="login-footer">
          <Text type="secondary" className="login-footer-text">
            © 2025 TgGod. 群组消息管理系统
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
