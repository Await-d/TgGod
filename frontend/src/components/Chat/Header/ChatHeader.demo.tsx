/**
 * ChatHeader Component Demo
 *
 * This file demonstrates the ChatHeader component usage
 * Run this in your development environment to test the component
 */

import React, { useState } from 'react';
import ChatHeader from './ChatHeader';
import type { ChatHeaderProps } from './ChatHeader';

export const ChatHeaderDemo: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleSearch = () => {
  };

  const handleToggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div style={{ width: '100%', height: '100vh', background: '#f5f5f5' }}>
      {/* Example 1: Full featured */}
      <ChatHeader
        groupName="Tech Discussion Group"
        groupAvatar="https://via.placeholder.com/40"
        memberCount={1234}
        onlineCount={89}
        onToggleSidebar={handleToggleSidebar}
        onSearch={handleSearch}
        showSidebarToggle={true}
      />

      {/* Example 2: Without avatar */}
      <div style={{ marginTop: '20px' }}>
        <ChatHeader
          groupName="Design Team"
          memberCount={567}
          onlineCount={45}
          onSearch={handleSearch}
        />
      </div>

      {/* Example 3: Minimal */}
      <div style={{ marginTop: '20px' }}>
        <ChatHeader
          groupName="Quick Chat"
        />
      </div>

      {/* Example 4: Long name test */}
      <div style={{ marginTop: '20px' }}>
        <ChatHeader
          groupName="This is a very long group name that should be truncated properly"
          memberCount={9999}
          onlineCount={999}
        />
      </div>
    </div>
  );
};

export default ChatHeaderDemo;
