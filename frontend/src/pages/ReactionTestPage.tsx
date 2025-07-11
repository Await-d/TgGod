import React from 'react';
import { Space, Typography, Card } from 'antd';
import MessageReactions from '../components/Chat/MessageReactions';

const { Title, Paragraph, Text } = Typography;

const ReactionTestPage: React.FC = () => {
  // 测试不同格式的 reactions 数据
  const testCases = [
    {
      title: '标准对象格式',
      reactions: { '❤': 4, '👍': 3, '😊': 1 }
    },
    {
      title: 'ReactionEmoji 数组格式',
      reactions: [
        { emoticon: '❤', count: 4 },
        { emoticon: '👍', count: 3 },
        { emoticon: '😊', count: 1 }
      ]
    },
    {
      title: '字符串格式 (Python 对象表示)',
      reactions: "ReactionEmoji(emoticon='❤') 4 ReactionEmoji(emoticon='👍') 3"
    },
    {
      title: '简单字符串格式',
      reactions: "❤ 4 👍 3 😊 1"
    },
    {
      title: '单个表情字符串',
      reactions: "ReactionEmoji(emoticon='❤')"
    },
    {
      title: '混合格式字符串',
      reactions: "❤4 👍3 😊1 💯2"
    }
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <Title level={2}>MessageReactions 组件测试</Title>
      <Paragraph>
        测试 MessageReactions 组件对不同格式的 reactions 数据的解析和显示功能。
      </Paragraph>

      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {testCases.map((testCase, index) => (
          <Card key={index} title={testCase.title} size="small">
            <div style={{ marginBottom: '16px' }}>
              <Text strong>原始数据: </Text>
              <Text code>{JSON.stringify(testCase.reactions)}</Text>
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <Text strong>渲染结果: </Text>
            </div>
            
            <div style={{ 
              padding: '12px', 
              border: '1px solid #d9d9d9', 
              borderRadius: '6px',
              backgroundColor: '#fafafa'
            }}>
              <MessageReactions reactions={testCase.reactions} />
            </div>
          </Card>
        ))}
      </Space>

      <Card 
        title="移动端测试" 
        style={{ marginTop: '24px' }}
        size="small"
      >
        <div style={{ marginBottom: '16px' }}>
          <Text strong>移动端样式: </Text>
        </div>
        <div style={{ 
          padding: '12px', 
          border: '1px solid #d9d9d9', 
          borderRadius: '6px',
          backgroundColor: '#fafafa'
        }}>
          <MessageReactions 
            reactions="ReactionEmoji(emoticon='❤') 4 ReactionEmoji(emoticon='👍') 3"
            isMobile={true}
          />
        </div>
      </Card>
    </div>
  );
};

export default ReactionTestPage;