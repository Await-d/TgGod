import React, { useState } from 'react';
import { Card, Input, Button, Space, Typography, Divider } from 'antd';
import { CopyOutlined, SendOutlined } from '@ant-design/icons';
import MarkdownRenderer, { isMarkdownContent } from './MarkdownRenderer';
import './MarkdownRenderer.css';

const { TextArea } = Input;
const { Title, Text } = Typography;

const MarkdownDemo: React.FC = () => {
  const [markdown, setMarkdown] = useState(`# Markdown 支持测试

## 功能特性

- **粗体文本** 和 *斜体文本*
- ~~删除线文本~~
- \`行内代码\`
- [链接示例](https://github.com)

### 代码块

\`\`\`javascript
function greet(name) {
  console.log(\`Hello, \${name}!\`);
}
\`\`\`

### 引用

> 这是一个引用块
> 可以包含多行内容

### 列表

1. 有序列表项 1
2. 有序列表项 2

- 无序列表项 A
- 无序列表项 B

### 表格

| 功能 | 状态 | 说明 |
|------|------|------|
| 粗体 | ✅ | 支持 |
| 斜体 | ✅ | 支持 |
| 代码 | ✅ | 支持 |

### 任务列表

- [x] 完成基础功能
- [ ] 添加高级功能
- [ ] 性能优化

---

**测试完成！** 🎉`);

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown);
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title level={2}>Markdown 消息支持测试</Title>
      <Text type="secondary">
        在消息中输入 Markdown 格式的文本，系统会自动检测并渲染为富文本显示
      </Text>
      
      <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
        <Card 
          title="Markdown 输入" 
          style={{ flex: 1 }}
          extra={
            <Space>
              <Button 
                icon={<CopyOutlined />} 
                onClick={handleCopy}
                size="small"
              >
                复制
              </Button>
              <Text type="secondary">
                {isMarkdownContent(markdown) ? '✅ 检测到 Markdown' : '❌ 普通文本'}
              </Text>
            </Space>
          }
        >
          <TextArea
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            rows={20}
            placeholder="输入 Markdown 内容..."
            style={{ fontFamily: 'Monaco, monospace', fontSize: '13px' }}
          />
        </Card>
        
        <Card title="渲染效果" style={{ flex: 1 }}>
          <div style={{ minHeight: '400px', maxHeight: '500px', overflowY: 'auto' }}>
            <Title level={4}>普通消息样式</Title>
            <div style={{ 
              background: '#f5f5f5', 
              padding: '12px 16px', 
              borderRadius: '12px',
              marginBottom: '16px'
            }}>
              <MarkdownRenderer content={markdown} />
            </div>
            
            <Title level={4}>自己发送的消息样式</Title>
            <div style={{ 
              background: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)', 
              color: 'white',
              padding: '12px 16px', 
              borderRadius: '12px',
              marginBottom: '16px'
            }}>
              <MarkdownRenderer content={markdown} isOwn={true} />
            </div>
          </div>
        </Card>
      </div>
      
      <Divider />
      
      <Card title="Markdown 语法说明" size="small">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
          <div>
            <Title level={5}>基础语法</Title>
            <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
{`# 标题 1
## 标题 2
**粗体**
*斜体*
~~删除线~~
\`行内代码\``}
            </pre>
          </div>
          
          <div>
            <Title level={5}>代码块</Title>
            <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
{`\`\`\`javascript
function test() {
  console.log('Hello');
}
\`\`\``}
            </pre>
          </div>
          
          <div>
            <Title level={5}>列表</Title>
            <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
{`1. 有序列表
2. 项目二

- 无序列表
- 项目 B`}
            </pre>
          </div>
          
          <div>
            <Title level={5}>其他</Title>
            <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
{`> 引用文本
[链接](http://example.com)
| 表格 | 列 |
|------|------|
| 单元格 | 值 |`}
            </pre>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default MarkdownDemo;