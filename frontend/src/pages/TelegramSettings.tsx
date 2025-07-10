import React from 'react';
import TelegramAuth from '../components/TelegramAuth';
import './TelegramSettings.css';

const TelegramSettings: React.FC = () => {
  const handleAuthSuccess = (userInfo: any) => {
    console.log('Telegram认证成功:', userInfo);
    // 可以在这里处理认证成功后的逻辑
    // 比如刷新群组列表、更新用户状态等
  };

  const handleAuthError = (error: string) => {
    console.error('Telegram认证失败:', error);
    // 可以在这里处理认证失败的逻辑
    // 比如显示错误通知等
  };

  return (
    <div className="telegram-settings">
      <div className="settings-header">
        <h1>Telegram 设置</h1>
        <p>配置您的 Telegram 连接以使用群组消息管理功能</p>
      </div>
      
      <div className="settings-content">
        <TelegramAuth 
          onAuthSuccess={handleAuthSuccess}
          onAuthError={handleAuthError}
        />
      </div>
      
      <div className="settings-info">
        <div className="info-card">
          <h3>功能说明</h3>
          <ul>
            <li>连接您的 Telegram 账户后可以管理群组消息</li>
            <li>支持获取群组列表和消息内容</li>
            <li>可以发送、删除、置顶消息</li>
            <li>支持消息搜索和过滤功能</li>
            <li>所有操作都通过 Telegram 官方 API 进行</li>
          </ul>
        </div>
        
        <div className="info-card">
          <h3>安全说明</h3>
          <ul>
            <li>认证信息仅存储在本地，不会上传到第三方服务器</li>
            <li>使用 Telegram 官方认证流程，安全可靠</li>
            <li>支持两步验证，保护账户安全</li>
            <li>可随时登出并清除本地认证信息</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default TelegramSettings;