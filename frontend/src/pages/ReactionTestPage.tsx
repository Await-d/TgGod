import React from 'react';
import { Space, Typography, Card } from 'antd';
import MessageReactions from '../components/Chat/MessageReactions';
import './ReactionTestPage.css';

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
    <div className="reaction-page">
      <Title level={2} className="reaction-title">MessageReactions 组件测试</Title>
      <Paragraph>
        测试 MessageReactions 组件对不同格式的 reactions 数据的解析和显示功能。
      </Paragraph>

      <Space direction="vertical" className="reaction-list" size="large">
        {testCases.map((testCase, index) => (
          <Card key={index} title={testCase.title} size="small">
            <div className="reaction-block">
              <Text strong>原始数据: </Text>
              <Text code>{JSON.stringify(testCase.reactions)}</Text>
            </div>
            
            <div className="reaction-block">
              <Text strong>渲染结果: </Text>
            </div>
            
            <div className="reaction-preview">
              <MessageReactions reactions={testCase.reactions} />
            </div>
          </Card>
        ))}
      </Space>

      <Card 
        title="移动端测试" 
        size="small"
        className="reaction-mobile-card"
      >
        <div className="reaction-block">
          <Text strong>移动端样式: </Text>
        </div>
        <div className="reaction-preview">
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
