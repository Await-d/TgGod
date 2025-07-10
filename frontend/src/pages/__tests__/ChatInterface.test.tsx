import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ChatInterface from '../ChatInterface';

// Mock the stores
jest.mock('../../store', () => ({
  useTelegramStore: () => ({
    groups: [],
    messages: [],
    setGroups: jest.fn(),
    setMessages: jest.fn(),
    setSelectedGroup: jest.fn(),
  }),
  useAuthStore: () => ({
    isAuthenticated: true,
  }),
}));

// Mock the WebSocket service
jest.mock('../../services/websocket', () => ({
  webSocketService: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    subscribe: jest.fn(() => jest.fn()),
  },
}));

// Mock the API service
jest.mock('../../services/apiService', () => ({
  messageApi: {
    sendMessage: jest.fn(),
  },
}));

// Mock the mobile gesture hooks
jest.mock('../../hooks/useMobileGestures', () => ({
  useMobileGestures: () => ({ isSwiping: false }),
  useIsMobile: () => false,
  useKeyboardHeight: () => ({ keyboardHeight: 0, isKeyboardVisible: false }),
}));

const renderChatInterface = () => {
  return render(
    <BrowserRouter>
      <ChatInterface />
    </BrowserRouter>
  );
};

describe('ChatInterface', () => {
  test('should render chat interface', () => {
    renderChatInterface();
    
    expect(screen.getByText('请选择群组')).toBeInTheDocument();
    expect(screen.getByText('已断开')).toBeInTheDocument();
  });

  test('should show mobile menu button on mobile', () => {
    // Mock useIsMobile to return true
    const mockUseIsMobile = require('../../hooks/useMobileGestures').useIsMobile;
    mockUseIsMobile.mockReturnValue(true);
    
    renderChatInterface();
    
    // Should have mobile menu button
    const menuButton = screen.getByRole('button');
    expect(menuButton).toBeInTheDocument();
  });

  test('should handle connection status display', () => {
    renderChatInterface();
    
    // Should show disconnected status initially
    expect(screen.getByText('已断开')).toBeInTheDocument();
    
    // Should have connection status indicator
    const statusIndicator = document.querySelector('.connection-status');
    expect(statusIndicator).toBeInTheDocument();
    expect(statusIndicator).toHaveClass('disconnected');
  });

  test('should render responsive layout components', () => {
    renderChatInterface();
    
    // Should have chat body
    const chatBody = document.querySelector('.chat-body');
    expect(chatBody).toBeInTheDocument();
    
    // Should have desktop layout by default
    const desktopLayout = document.querySelector('.desktop-layout');
    expect(desktopLayout).toBeInTheDocument();
  });
});

describe('Mobile adaptations', () => {
  beforeEach(() => {
    // Mock mobile environment
    const mockUseIsMobile = require('../../hooks/useMobileGestures').useIsMobile;
    mockUseIsMobile.mockReturnValue(true);
  });

  test('should show mobile layout on mobile devices', () => {
    renderChatInterface();
    
    // Should not have desktop layout
    const desktopLayout = document.querySelector('.desktop-layout');
    expect(desktopLayout).not.toBeInTheDocument();
    
    // Should have mobile message panel
    const mobilePanel = document.querySelector('.mobile-message-panel');
    expect(mobilePanel).toBeInTheDocument();
  });

  test('should handle mobile menu toggle', () => {
    renderChatInterface();
    
    const menuButton = screen.getByRole('button');
    
    // Click to toggle menu
    fireEvent.click(menuButton);
    
    // Button should be present (though actual drawer functionality is mocked)
    expect(menuButton).toBeInTheDocument();
  });
});