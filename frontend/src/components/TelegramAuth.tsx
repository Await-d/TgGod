import React, { useState, useEffect } from 'react';
import './TelegramAuth.css';
import { apiService } from '../services/api';

interface UserInfo {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  phone?: string;
}

interface AuthStatus {
  is_authorized: boolean;
  user_info?: UserInfo;
  message: string;
}

interface LoginResponse {
  user_info: UserInfo;
  message?: string;
}

interface TelegramAuthProps {
  onAuthSuccess?: (userInfo: any) => void;
  onAuthError?: (error: string) => void;
}

const TelegramAuth: React.FC<TelegramAuthProps> = ({ onAuthSuccess, onAuthError }) => {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [needsPassword, setNeedsPassword] = useState(false);
  const [step, setStep] = useState<'check' | 'phone' | 'code' | 'password' | 'success'>('check');
  const [error, setError] = useState('');

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    setLoading(true);
    try {
      console.log('正在检查Telegram认证状态...');
      const response = await apiService.get('/telegram/auth/status');
      
      // 详细日志记录API响应
      console.log('Telegram auth status response:', response);
      
      if (response.success && response.data) {
        const data = response.data as AuthStatus;
        console.log('Telegram auth status data:', data);
        setAuthStatus(data);

        if (data.is_authorized) {
          setStep('success');
          onAuthSuccess?.(data.user_info);
        } else {
          setStep('phone');
        }
      } else {
        // 记录错误信息以便调试
        console.warn('Telegram认证状态检查失败:', response);
        const errorMsg = response.message || '检查认证状态失败';
        setError(errorMsg);
        
        // 如果响应中包含更具体的错误信息，则使用它
        const responseData = response.data as any;
        if (responseData?.message) {
          setError(responseData.message);
          onAuthError?.(responseData.message);
        } else {
          onAuthError?.(errorMsg);
        }
      }
    } catch (err: any) {
      console.error('Telegram认证状态检查异常:', err);
      const errorMsg = err.message || '检查认证状态失败';
      setError(errorMsg);
      onAuthError?.(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const sendCode = async () => {
    if (!phone.trim()) {
      setError('请输入手机号码');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await apiService.post('/telegram/auth/send-code', { phone });

      if (response.success) {
        setStep('code');
      } else {
        setError(response.message || '发送验证码失败');
        onAuthError?.(response.message || '发送验证码失败');
      }
    } catch (err) {
      setError('发送验证码失败');
      onAuthError?.('发送验证码失败');
    } finally {
      setLoading(false);
    }
  };

  const login = async () => {
    if (!code.trim()) {
      setError('请输入验证码');
      return;
    }

    if (needsPassword && !password.trim()) {
      setError('请输入两步验证密码');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const payload = {
        phone,
        code,
        password: needsPassword ? password : undefined,
      };

      const response = await apiService.post('/telegram/auth/login', payload);

      if (response.success && response.data) {
        const userData = response.data as LoginResponse;
        setStep('success');
        setAuthStatus({
          is_authorized: true,
          user_info: userData.user_info,
          message: userData.message || '认证成功',
        });
        onAuthSuccess?.(userData.user_info);
      } else {
        if (response.message === '需要两步验证密码') {
          setNeedsPassword(true);
          setStep('password');
        } else {
          setError(response.message || '登录失败');
          onAuthError?.(response.message || '登录失败');
        }
      }
    } catch (err) {
      setError('登录失败');
      onAuthError?.('登录失败');
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      const response = await apiService.post('/telegram/auth/logout');

      if (response.success) {
        setAuthStatus(null);
        setStep('phone');
        setPhone('');
        setCode('');
        setPassword('');
        setNeedsPassword(false);
        setError('');
      } else {
        setError(response.message || '登出失败');
      }
    } catch (err) {
      setError('登出失败');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setStep('phone');
    setPhone('');
    setCode('');
    setPassword('');
    setNeedsPassword(false);
    setError('');
  };

  if (loading && step === 'check') {
    return (
      <div className="telegram-auth-container">
        <div className="auth-card">
          <div className="loading-spinner">
            <div className="spinner"></div>
            <p>检查认证状态...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="telegram-auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2>Telegram 认证</h2>
          <p>连接您的 Telegram 账户以使用群组消息功能</p>
        </div>

        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        {step === 'phone' && (
          <div className="auth-form">
            <div className="form-group">
              <label htmlFor="phone">手机号码</label>
              <input
                id="phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1234567890"
                disabled={loading}
              />
              <small>请输入完整的国际手机号码，包含国家代码</small>
            </div>
            <button
              onClick={sendCode}
              disabled={loading || !phone.trim()}
              className="auth-button primary"
            >
              {loading ? '发送中...' : '发送验证码'}
            </button>
          </div>
        )}

        {step === 'code' && (
          <div className="auth-form">
            <div className="form-group">
              <label htmlFor="phone-display">手机号码</label>
              <input
                id="phone-display"
                type="text"
                value={phone}
                disabled
                className="readonly"
              />
            </div>
            <div className="form-group">
              <label htmlFor="code">验证码</label>
              <input
                id="code"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="请输入收到的验证码"
                disabled={loading}
                maxLength={6}
              />
              <small>请检查您的 Telegram 应用，输入收到的验证码</small>
            </div>
            <div className="button-group">
              <button
                onClick={resetForm}
                disabled={loading}
                className="auth-button secondary"
              >
                重新开始
              </button>
              <button
                onClick={login}
                disabled={loading || !code.trim()}
                className="auth-button primary"
              >
                {loading ? '验证中...' : '验证登录'}
              </button>
            </div>
          </div>
        )}

        {step === 'password' && (
          <div className="auth-form">
            <div className="form-group">
              <label htmlFor="password">两步验证密码</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入两步验证密码"
                disabled={loading}
              />
              <small>您的账户开启了两步验证，请输入密码</small>
            </div>
            <div className="button-group">
              <button
                onClick={resetForm}
                disabled={loading}
                className="auth-button secondary"
              >
                重新开始
              </button>
              <button
                onClick={login}
                disabled={loading || !password.trim()}
                className="auth-button primary"
              >
                {loading ? '验证中...' : '完成登录'}
              </button>
            </div>
          </div>
        )}

        {step === 'success' && authStatus?.is_authorized && (
          <div className="auth-success">
            <div className="success-icon">✅</div>
            <h3>认证成功</h3>
            <div className="user-info">
              <p><strong>用户:</strong> {authStatus.user_info?.first_name} {authStatus.user_info?.last_name}</p>
              {authStatus.user_info?.username && (
                <p><strong>用户名:</strong> @{authStatus.user_info.username}</p>
              )}
              {authStatus.user_info?.phone && (
                <p><strong>手机:</strong> {authStatus.user_info.phone}</p>
              )}
            </div>
            <button
              onClick={logout}
              disabled={loading}
              className="auth-button secondary"
            >
              {loading ? '登出中...' : '登出账户'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TelegramAuth;