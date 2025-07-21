# 批量下载功能实现

## 功能概述

已成功在后端实现了支持多个文件同时下载的功能，包含以下主要特性：

### 🚀 新增API接口

#### 1. 批量下载启动接口
- **路径**: `POST /api/media/batch-download`
- **功能**: 启动多个文件的批量下载任务
- **参数**:
  ```json
  {
    "message_ids": [1, 2, 3, 4, 5],
    "force": false,
    "max_concurrent": 3
  }
  ```
- **响应**:
  ```json
  {
    "batch_id": "batch_abc12345",
    "status": "started",
    "message": "批量下载任务已启动，包含 5 个文件",
    "total_files": 5,
    "started_downloads": [1, 2, 3, 5],
    "already_downloaded": [4],
    "failed_to_start": []
  }
  ```

#### 2. 批量下载状态查询接口
- **路径**: `GET /api/media/batch-status/{batch_id}`
- **功能**: 查询批量下载任务的整体状态和每个文件的详细状态
- **响应**:
  ```json
  {
    "batch_id": "batch_abc12345",
    "total_files": 5,
    "completed": 2,
    "downloading": 1,
    "failed": 0,
    "pending": 2,
    "overall_status": "in_progress",
    "files": [
      {
        "message_id": 1,
        "status": "completed",
        "progress": 100,
        "file_path": "./media/photos/1_123_abc.jpg",
        "download_url": "/media/photos/1_123_abc.jpg"
      },
      {
        "message_id": 2,
        "status": "downloading",
        "progress": 45,
        "downloaded_size": 450000,
        "total_size": 1000000,
        "download_speed": 50000,
        "estimated_time_remaining": 11
      }
    ]
  }
  ```

#### 3. 批量下载取消接口
- **路径**: `POST /api/media/batch-cancel/{batch_id}`
- **功能**: 取消批量下载任务，停止所有相关的下载
- **响应**:
  ```json
  {
    "status": "cancelled",
    "message": "批量下载任务已取消，取消了 3 个下载",
    "batch_id": "batch_abc12345",
    "cancelled_downloads": 3,
    "total_files": 5
  }
  ```

### ⚡ 核心技术特性

#### 1. 并发控制
- **智能信号量机制**: 使用 `asyncio.Semaphore` 控制同时下载的文件数量
- **可配置并发数**: 支持 1-5 个并发下载，默认3个并发
- **资源保护**: 防止过多并发导致系统资源耗尽

#### 2. 状态管理
- **批量任务跟踪**: 每个批量下载任务都有唯一ID和状态跟踪
- **实时进度监控**: 支持查询整体进度和单个文件进度
- **状态持久化**: 下载状态保存在数据库中，重启不丢失

#### 3. 错误处理
- **分类处理**: 区分已下载、下载失败、消息不存在等不同情况
- **优雅降级**: 部分文件失败不影响其他文件下载
- **详细错误信息**: 提供具体的错误原因和建议

#### 4. 队列整合
- **复用现有队列**: 与单文件下载共享同一个下载队列
- **避免重复下载**: 检测已在下载中的文件，避免重复添加
- **取消机制**: 支持优雅取消正在进行的下载任务

### 🏗️ 架构设计

```
批量下载请求
    ↓
验证和分类消息
    ↓
创建批量任务记录
    ↓
启动批量下载管理器
    ↓
[并发控制] → 单文件下载任务 → 添加到下载队列
    ↓                              ↓
监控和状态更新 ← 下载工作进程 ← 队列处理
```

#### 关键组件
1. **BatchDownloadManager**: 管理整个批量下载生命周期
2. **BatchSemaphore**: 控制并发下载数量
3. **DownloadQueue**: 串行处理所有下载任务（单个+批量）
4. **StatusTracker**: 跟踪每个文件的下载状态

### 📊 性能优化

#### 1. 内存管理
- **短连接数据库**: 避免长时间持有数据库连接
- **及时资源释放**: 完成后清理信号量和批量任务记录
- **分批处理**: 限制单次批量下载最多50个文件

#### 2. 网络优化
- **智能并发**: 避免过多并发连接影响Telegram API
- **进度批量更新**: 每秒最多更新一次数据库，减少I/O
- **断点续传支持**: 继承原有的下载进度跟踪机制

#### 3. 用户体验
- **即时反馈**: 启动请求立即返回，不等待下载完成
- **实时状态**: 支持轮询查询下载进度
- **灵活配置**: 用户可控制并发数和强制下载选项

### 🔧 使用示例

#### JavaScript 前端调用示例
```javascript
// 1. 启动批量下载
const batchRequest = {
  message_ids: [101, 102, 103, 104, 105],
  force: false,
  max_concurrent: 3
};

const response = await fetch('/api/media/batch-download', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(batchRequest)
});

const batchInfo = await response.json();
const batchId = batchInfo.batch_id;

// 2. 轮询查询状态
const pollStatus = async () => {
  const statusResponse = await fetch(`/api/media/batch-status/${batchId}`);
  const status = await statusResponse.json();
  
  console.log(`进度: ${status.completed}/${status.total_files} 完成`);
  
  if (status.overall_status === 'completed') {
    console.log('批量下载完成!');
    clearInterval(statusInterval);
  } else if (status.overall_status === 'failed') {
    console.log('批量下载失败');
    clearInterval(statusInterval);
  }
};

const statusInterval = setInterval(pollStatus, 2000);

// 3. 可选：取消下载
const cancelDownload = async () => {
  await fetch(`/api/media/batch-cancel/${batchId}`, { method: 'POST' });
  clearInterval(statusInterval);
};
```

### 🛠️ 技术实现细节

#### 数据模型
```python
class BatchDownloadRequest(BaseModel):
    message_ids: List[int]          # 消息ID列表
    force: bool = False             # 强制重新下载
    max_concurrent: int = 3         # 最大并发数

class BatchDownloadResponse(BaseModel):
    batch_id: str                   # 批量任务ID
    status: str                     # 任务状态
    message: str                    # 状态描述
    total_files: int                # 总文件数
    started_downloads: List[int]    # 开始下载的消息ID
    already_downloaded: List[int]   # 已下载的消息ID
    failed_to_start: List[dict]     # 启动失败的消息详情
```

#### 核心算法
```python
async def batch_download_manager(batch_id: str):
    """批量下载管理器 - 控制整个批量下载流程"""
    # 1. 创建信号量控制并发
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # 2. 为每个文件创建下载任务
    tasks = []
    for message_id in message_ids:
        task = asyncio.create_task(
            batch_download_single_file(batch_id, message_id, force, semaphore)
        )
        tasks.append(task)
    
    # 3. 并发执行所有任务（受信号量限制）
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # 4. 清理资源
    cleanup_batch_resources(batch_id)

async def batch_download_single_file(batch_id, message_id, force, semaphore):
    """单个文件下载任务 - 受信号量控制的并发执行"""
    async with semaphore:  # 获取信号量许可
        # 检查任务是否被取消
        if is_batch_cancelled(batch_id):
            return
        
        # 添加到现有下载队列
        await download_queue.put((message_id, force))
```

### ✅ 兼容性保证

1. **向后兼容**: 原有单文件下载接口完全保持不变
2. **共享队列**: 批量下载和单文件下载使用同一个下载队列，避免冲突
3. **数据库兼容**: 复用现有的消息表和下载状态字段
4. **API一致性**: 响应格式与现有API风格保持一致

### 🔒 安全考虑

1. **请求限制**: 单次批量下载最多50个文件
2. **并发限制**: 最大5个并发下载，防止资源滥用
3. **权限检查**: 继承原有的消息访问权限验证
4. **资源清理**: 及时清理批量任务记录，避免内存泄漏

## 总结

批量下载功能已成功实现，提供了完整的API接口、强大的并发控制、详细的状态跟踪和优雅的错误处理。该功能与现有系统完全兼容，能够大幅提升用户批量下载文件的效率和体验。