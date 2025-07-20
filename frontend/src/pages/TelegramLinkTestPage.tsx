import React, { useState } from 'react';
import { Card, Space, Input, Button, Typography, Divider } from 'antd';
import TelegramLinkPreview from '../components/Chat/TelegramLinkPreview';
import EnhancedMessageText from '../components/Chat/EnhancedMessageText';

const { Title, Text } = Typography;
const { TextArea } = Input;

const TelegramLinkTestPage: React.FC = () => {
  const [testUrl, setTestUrl] = useState('https://t.me/setlanguage/zhlangcn');
  const [testMessage, setTestMessage] = useState('查看这个链接：https://t.me/setlanguage/zhlangcn 很有用！');

  // 模拟群组跳转处理
  const handleJumpToGroup = (groupId: number) => {
    console.log('TelegramLinkTestPage - jumping to group:', groupId);
    alert(`模拟跳转到群组 ID: ${groupId}`);
  };

  // 测试链接列表
  const testLinks = [
    'https://t.me/setlanguage/zhlangcn',
    'https://t.me/testgroup',
    'https://t.me/+ABC123DEFGH',
    'https://t.me/examplegroup',
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <Title level={2}>Telegram链接预览测试页面</Title>
      
      <Card title="单个链接测试" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>测试URL:</Text>
            <Input
              value={testUrl}
              onChange={(e) => setTestUrl(e.target.value)}
              placeholder="输入Telegram链接"
              style={{ marginTop: 8 }}
            />
          </div>
          
          <div>
            <Text strong>预览效果:</Text>
            <div style={{ marginTop: 8 }}>
              <TelegramLinkPreview
                url={testUrl}
                onJumpToGroup={handleJumpToGroup}
              />
            </div>
          </div>
        </Space>
      </Card>

      <Card title="消息文本中的链接测试" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>测试消息:</Text>
            <TextArea
              value={testMessage}
              onChange={(e) => setTestMessage(e.target.value)}
              placeholder="输入包含Telegram链接的消息文本"
              rows={3}
              style={{ marginTop: 8 }}
            />
          </div>
          
          <div>
            <Text strong>增强消息文本效果:</Text>
            <div style={{ 
              marginTop: 8, 
              padding: 16, 
              background: '#f5f5f5', 
              borderRadius: 8,
              border: '1px solid #d9d9d9'
            }}>
              <EnhancedMessageText
                text={testMessage}
                onJumpToGroup={handleJumpToGroup}
              />
            </div>
          </div>
        </Space>
      </Card>

      <Card title="预设链接测试">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text strong>点击下面的按钮测试不同类型的链接:</Text>
          
          <Space wrap>
            {testLinks.map((link, index) => (
              <Button
                key={index}
                onClick={() => setTestUrl(link)}
                type={testUrl === link ? 'primary' : 'default'}
              >
                {link.includes('setlanguage') ? '语言设置' : 
                 link.includes('+') ? '私有群组' : 
                 '公开群组'}
              </Button>
            ))}
          </Space>
          
          <Divider />
          
          {testLinks.map((link, index) => (
            <div key={index} style={{ marginBottom: 16 }}>
              <Text type="secondary">{link}</Text>
              <TelegramLinkPreview
                url={link}
                onJumpToGroup={handleJumpToGroup}
              />
            </div>
          ))}
        </Space>
      </Card>
    </div>
  );
};

export default TelegramLinkTestPage;