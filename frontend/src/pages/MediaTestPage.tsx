import React, { useState, useEffect } from 'react';
import { Card, List, Typography, Space, Button, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import MessageBubble from '../components/Chat/MessageBubble';
import { TelegramMessage } from '../types';

const { Title, Paragraph } = Typography;

const MediaTestPage: React.FC = () => {
  const [messages, setMessages] = useState<TelegramMessage[]>([]);
  const [loading, setLoading] = useState(false);

  // 模拟获取消息数据
  const fetchMessages = async () => {
    setLoading(true);
    try {
      // 创建测试消息数据
      const testMessages: TelegramMessage[] = [
        {
          id: 1,
          group_id: 1,
          message_id: 1001,
          sender_id: 1001,
          sender_username: 'test_user',
          sender_name: '测试用户',
          text: '这是一张测试图片',
          media_type: 'photo',
          media_path: 'media/photos/test.jpg',
          media_size: 4143,
          media_filename: 'test.jpg',
          view_count: 5,
          is_forwarded: false,
          forwarded_from: undefined,
          is_own_message: false,
          reply_to_message_id: undefined,
          edit_date: undefined,
          is_pinned: false,
          reactions: undefined,
          mentions: undefined,
          hashtags: undefined,
          urls: undefined,
          date: new Date().toISOString(),
          created_at: new Date().toISOString(),
          updated_at: undefined
        },
        {
          id: 2,
          group_id: 1,
          message_id: 1002,
          sender_id: 1002,
          sender_username: 'video_user',
          sender_name: '视频用户',
          text: '这是一个测试视频',
          media_type: 'video',
          media_path: 'media/videos/test.mp4',
          media_size: 1024,
          media_filename: 'test.mp4',
          view_count: 8,
          is_forwarded: false,
          forwarded_from: undefined,
          is_own_message: false,
          reply_to_message_id: undefined,
          edit_date: undefined,
          is_pinned: false,
          reactions: undefined,
          mentions: undefined,
          hashtags: undefined,
          urls: undefined,
          date: new Date().toISOString(),
          created_at: new Date().toISOString(),
          updated_at: undefined
        },
        {
          id: 3,
          group_id: 1,
          message_id: 1003,
          sender_id: 1003,
          sender_username: 'audio_user',
          sender_name: '音频用户',
          text: '这是一个测试音频文件',
          media_type: 'audio',
          media_path: 'media/audios/test.mp3',
          media_size: 512,
          media_filename: 'test.mp3',
          view_count: 3,
          is_forwarded: false,
          forwarded_from: undefined,
          is_own_message: false,
          reply_to_message_id: undefined,
          edit_date: undefined,
          is_pinned: false,
          reactions: undefined,
          mentions: undefined,
          hashtags: undefined,
          urls: undefined,
          date: new Date().toISOString(),
          created_at: new Date().toISOString(),
          updated_at: undefined
        },
        {
          id: 4,
          group_id: 1,
          message_id: 1004,
          sender_id: 1004,
          sender_username: 'doc_user',
          sender_name: '文档用户',
          text: '这是一个测试文档',
          media_type: 'document',
          media_path: 'media/documents/test.txt',
          media_size: 256,
          media_filename: 'test.txt',
          view_count: 2,
          is_forwarded: false,
          forwarded_from: undefined,
          is_own_message: false,
          reply_to_message_id: undefined,
          edit_date: undefined,
          is_pinned: true,
          reactions: undefined,
          mentions: undefined,
          hashtags: undefined,
          urls: undefined,
          date: new Date().toISOString(),
          created_at: new Date().toISOString(),
          updated_at: undefined
        }
      ];
      
      setMessages(testMessages);
      message.success('测试消息加载完成');
    } catch (error) {
      console.error('加载消息失败:', error);
      message.error('加载消息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, []);

  const handleReply = (message: TelegramMessage) => {
    console.log('Reply to message:', message);
  };

  const handleCreateRule = (message: TelegramMessage) => {
    console.log('Create rule from message:', message);
  };

  const handleDelete = (messageId: number) => {
    console.log('Delete message:', messageId);
  };

  const handleJumpToGroup = (groupId: number) => {
    console.log('跳转到群组:', groupId);
    message.info(`模拟跳转到群组 ID: ${groupId}`);
  };

  return (
    <div style={{ padding: '20px' }}>
      <Card>
        <div style={{ marginBottom: '20px' }}>
          <Title level={2}>媒体预览测试页面</Title>
          <Paragraph>
            这个页面用于测试各种媒体类型的预览功能，包括图片、视频、音频和文档。
          </Paragraph>
          <Button 
            type="primary" 
            icon={<ReloadOutlined />} 
            onClick={fetchMessages}
            loading={loading}
          >
            重新加载测试数据
          </Button>
        </div>

        <List
          dataSource={messages}
          renderItem={(message) => (
            <List.Item key={message.id}>
              <div style={{ width: '100%', maxWidth: '800px' }}>
                <MessageBubble
                  message={message}
                  isOwn={false}
                  showAvatar={true}
                  onReply={handleReply}
                  onCreateRule={handleCreateRule}
                  onDelete={handleDelete}
                  onJumpToGroup={handleJumpToGroup}
                />
              </div>
            </List.Item>
          )}
          loading={loading}
        />
      </Card>
    </div>
  );
};

export default MediaTestPage;