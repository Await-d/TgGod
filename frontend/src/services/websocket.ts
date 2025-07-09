import { io, Socket } from 'socket.io-client';
import { WebSocketMessage } from '../types';

class WebSocketService {
  private socket: Socket | null = null;
  private clientId: string = '';
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000;

  constructor() {
    this.clientId = this.generateClientId();
  }

  // 生成客户端ID
  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // 连接WebSocket
  connect(): void {
    if (this.socket?.connected) {
      return;
    }

    const wsUrl = `ws://localhost:8001/ws/${this.clientId}`;
    this.socket = io(wsUrl, {
      transports: ['websocket'],
      autoConnect: true,
    });

    this.setupEventHandlers();
  }

  // 设置事件处理器
  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket连接成功');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket连接断开');
      this.handleReconnect();
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket错误:', error);
    });

    this.socket.on('message', (message: WebSocketMessage) => {
      this.handleMessage(message);
    });
  }

  // 处理重连
  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
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
    if (this.socket?.connected) {
      this.socket.emit('message', message);
    } else {
      console.warn('WebSocket未连接，消息发送失败');
    }
  }

  // 断开连接
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  // 获取连接状态
  isConnected(): boolean {
    return this.socket?.connected || false;
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

export default webSocketService;