// WebSocket service using native WebSocket
import { WebSocketMessage } from '../types';

class WebSocketService {
  private socket: WebSocket | null = null;
  private clientId: string = '';
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000;
  private reconnectTimer: NodeJS.Timeout | null = null;

  constructor() {
    this.clientId = this.generateClientId();
  }

  // 生成客户端ID
  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // 连接WebSocket
  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    // 获取WebSocket URL
    const wsUrl = process.env.REACT_APP_WS_URL 
      ? (() => {
          const wsBaseUrl = process.env.REACT_APP_WS_URL;
          let finalUrl: string;
          
          // 如果是完整URL（包含协议），直接使用
          if (wsBaseUrl.startsWith('ws://') || wsBaseUrl.startsWith('wss://')) {
            finalUrl = `${wsBaseUrl}/ws/${this.clientId}`;
          } else {
            // 如果是相对路径，构建完整URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            finalUrl = `${protocol}//${host}${wsBaseUrl}/${this.clientId}`;
          }
          
          console.log('WebSocket连接配置:', {
            baseUrl: wsBaseUrl,
            clientId: this.clientId,
            finalUrl: finalUrl
          });
          
          return finalUrl;
        })()
      : (() => {
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const host = window.location.host;
          const finalUrl = `${protocol}//${host}/ws/${this.clientId}`;
          
          console.log('WebSocket连接配置 (默认):', {
            clientId: this.clientId,
            finalUrl: finalUrl
          });
          
          return finalUrl;
        })();
    
    try {
      this.socket = new WebSocket(wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      console.error('WebSocket连接失败:', error);
      this.handleReconnect();
    }
  }

  // 设置事件处理器
  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.onopen = () => {
      console.log('WebSocket连接成功');
      this.reconnectAttempts = 0;
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.socket.onclose = (event) => {
      console.log('WebSocket连接断开:', event.code, event.reason);
      this.handleReconnect();
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket错误:', error);
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
      }
    };
  }

  // 处理重连
  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      this.reconnectTimer = setTimeout(() => {
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('WebSocket重连失败，已达到最大重试次数');
    }
  }

  // 处理消息
  private handleMessage(message: WebSocketMessage): void {
    const event = new CustomEvent('websocket-message', {
      detail: message,
    });
    window.dispatchEvent(event);
  }

  // 发送消息
  send(message: any): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket未连接，消息发送失败');
    }
  }

  // 断开连接
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  // 获取连接状态
  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  // 订阅特定类型的消息
  subscribe(type: string, callback: (data: any) => void): () => void {
    const handleMessage = (event: CustomEvent<WebSocketMessage>) => {
      const message = event.detail;
      if (message.type === type) {
        callback(message.data);
      }
    };

    window.addEventListener('websocket-message', handleMessage as EventListener);

    // 返回取消订阅函数
    return () => {
      window.removeEventListener('websocket-message', handleMessage as EventListener);
    };
  }
}

// 创建全局WebSocket服务实例
export const webSocketService = new WebSocketService();

// 便捷的订阅方法
export const subscribeToLogs = (callback: (log: any) => void) => {
  return webSocketService.subscribe('log', callback);
};

export const subscribeToProgress = (callback: (progress: any) => void) => {
  return webSocketService.subscribe('progress', callback);
};

export const subscribeToStatus = (callback: (status: any) => void) => {
  return webSocketService.subscribe('status', callback);
};

export const subscribeToNotification = (callback: (notification: any) => void) => {
  return webSocketService.subscribe('notification', callback);
};

// 新增：订阅实时消息
export const subscribeToMessages = (callback: (message: any) => void) => {
  return webSocketService.subscribe('message', callback);
};

// 新增：订阅群组状态更新
export const subscribeToGroupStatus = (callback: (status: any) => void) => {
  return webSocketService.subscribe('group_status', callback);
};

// 新增：订阅消息统计更新
export const subscribeToMessageStats = (callback: (stats: any) => void) => {
  return webSocketService.subscribe('message_stats', callback);
};

export default webSocketService;