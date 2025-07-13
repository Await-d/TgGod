import React, { useState, useEffect } from 'react';
import { Button, Card, Typography, Space, Alert } from 'antd';
import { webSocketService } from '../services/websocket';

const { Title, Text } = Typography;

const WebSocketTest: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [lastMessage, setLastMessage] = useState<any>(null);

  useEffect(() => {
    // 检查连接状态
    const checkConnection = () => {
      setIsConnected(webSocketService.isConnected());
    };

    // 订阅所有类型的消息用于测试
    const unsubscribeProgress = webSocketService.subscribe('monthly_sync_progress', (data) => {
      console.log('收到月度同步进度消息:', data);
      setLastMessage({ type: 'monthly_sync_progress', data, timestamp: new Date().toISOString() });
      setMessages(prev => [...prev, { type: 'monthly_sync_progress', data, timestamp: new Date().toISOString() }]);
    });

    const unsubscribeComplete = webSocketService.subscribe('monthly_sync_complete', (data) => {
      console.log('收到月度同步完成消息:', data);
      setLastMessage({ type: 'monthly_sync_complete', data, timestamp: new Date().toISOString() });
      setMessages(prev => [...prev, { type: 'monthly_sync_complete', data, timestamp: new Date().toISOString() }]);
    });

    // 定期检查连接状态
    const interval = setInterval(checkConnection, 1000);

    checkConnection();

    return () => {
      clearInterval(interval);
      unsubscribeProgress();
      unsubscribeComplete();
    };
  }, []);

  const handleConnect = () => {
    console.log('手动连接WebSocket');
    webSocketService.connect();
    setTimeout(() => setIsConnected(webSocketService.isConnected()), 1000);
  };

  const handleDisconnect = () => {
    console.log('手动断开WebSocket');
    webSocketService.disconnect();
    setIsConnected(false);
  };

  const handleSendTest = () => {
    console.log('发送测试消息');
    webSocketService.send({
      type: 'test',
      data: 'Hello from frontend',
      timestamp: new Date().toISOString()
    });
  };

  const clearMessages = () => {
    setMessages([]);
    setLastMessage(null);
  };

  return (
    <Card title="WebSocket 连接测试" style={{ margin: '20px' }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Text strong>连接状态: </Text>
          <Text style={{ color: isConnected ? 'green' : 'red' }}>
            {isConnected ? '已连接' : '未连接'}
          </Text>
        </div>

        <Space>
          <Button onClick={handleConnect} disabled={isConnected}>
            连接
          </Button>
          <Button onClick={handleDisconnect} disabled={!isConnected}>
            断开
          </Button>
          <Button onClick={handleSendTest} disabled={!isConnected}>
            发送测试消息
          </Button>
          <Button onClick={clearMessages}>
            清空消息
          </Button>
        </Space>

        {lastMessage && (
          <Alert
            message="最新消息"
            description={
              <div>
                <div><strong>类型:</strong> {lastMessage.type}</div>
                <div><strong>时间:</strong> {lastMessage.timestamp}</div>
                <div><strong>数据:</strong> {JSON.stringify(lastMessage.data, null, 2)}</div>
              </div>
            }
            type="info"
          />
        )}

        <div>
          <Title level={4}>消息历史 ({messages.length})</Title>
          <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #d9d9d9', padding: '10px' }}>
            {messages.map((msg, index) => (
              <div key={index} style={{ marginBottom: '10px', padding: '8px', backgroundColor: '#f5f5f5' }}>
                <div><strong>{msg.type}</strong> - {msg.timestamp}</div>
                <div style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {JSON.stringify(msg.data, null, 2)}
                </div>
              </div>
            ))}
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', color: '#999' }}>暂无消息</div>
            )}
          </div>
        </div>
      </Space>
    </Card>
  );
};

export default WebSocketTest;