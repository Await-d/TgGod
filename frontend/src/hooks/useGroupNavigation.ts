import { useEffect, useCallback } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { TelegramGroup } from '../types';
import { useTelegramStore } from '../store';

export interface GroupNavigationOptions {
  autoLoadMessages?: boolean;
  persistSelectedGroup?: boolean;
  syncOnGroupChange?: boolean;
}

/**
 * 群组导航和状态管理 Hook
 * 支持URL参数同步、自动消息加载、状态持久化
 */
export const useGroupNavigation = (options: GroupNavigationOptions = {}) => {
  const {
    autoLoadMessages = true,
    persistSelectedGroup = true,
    syncOnGroupChange = true
  } = options;

  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const { 
    groups, 
    selectedGroup, 
    messages,
    setSelectedGroup, 
    setMessages 
  } = useTelegramStore();

  // 从URL参数恢复选中群组
  const restoreGroupFromUrl = useCallback(() => {
    const groupId = searchParams.get('group');
    if (groupId && groups.length > 0) {
      const group = groups.find(g => g.id.toString() === groupId);
      if (group && (!selectedGroup || selectedGroup.id.toString() !== groupId)) {
        console.log('从URL恢复群组:', group.title);
        setSelectedGroup(group);
        return group;
      }
    }
    return null;
  }, [searchParams, groups, selectedGroup, setSelectedGroup]);

  // 将选中群组同步到URL
  const syncGroupToUrl = useCallback((group: TelegramGroup | null) => {
    if (!persistSelectedGroup) return;

    const newSearchParams = new URLSearchParams(searchParams);
    
    if (group) {
      newSearchParams.set('group', group.id.toString());
    } else {
      newSearchParams.delete('group');
    }

    // 只有当URL参数实际变化时才更新
    const newParamsString = newSearchParams.toString();
    const currentParamsString = searchParams.toString();
    
    if (newParamsString !== currentParamsString) {
      setSearchParams(newSearchParams, { replace: true });
    }
  }, [searchParams, setSearchParams, persistSelectedGroup]);

  // 选择群组的主要方法
  const selectGroup = useCallback(async (group: TelegramGroup | null) => {
    console.log('选择群组:', group?.title || '无');
    
    // 更新选中状态
    setSelectedGroup(group);
    
    // 同步到URL
    syncGroupToUrl(group);
    
    // 清空当前消息（避免显示错误的消息）
    setMessages([]);
    
    // 如果启用自动加载消息且选择了群组
    if (autoLoadMessages && group) {
      try {
        // 这里可以调用消息加载逻辑
        console.log('自动加载群组消息:', group.id);
        // TODO: 实际的消息加载逻辑将在后续实现
      } catch (error) {
        console.error('自动加载消息失败:', error);
      }
    }
  }, [setSelectedGroup, syncGroupToUrl, setMessages, autoLoadMessages]);

  // 监听URL参数变化和群组数据变化
  useEffect(() => {
    if (groups.length > 0) {
      const restoredGroup = restoreGroupFromUrl();
      
      // 如果没有从URL恢复群组，且当前也没有选中群组，可以选择默认群组
      if (!restoredGroup && !selectedGroup && groups.length > 0) {
        // 可以选择第一个活跃的群组作为默认
        const defaultGroup = groups.find(g => g.is_active) || groups[0];
        if (defaultGroup) {
          console.log('选择默认群组:', defaultGroup.title);
          selectGroup(defaultGroup);
        }
      }
    }
  }, [restoreGroupFromUrl, groups, selectedGroup, selectGroup]);

  // 监听群组变化，同步到URL
  useEffect(() => {
    if (syncOnGroupChange) {
      syncGroupToUrl(selectedGroup);
    }
  }, [selectedGroup, syncOnGroupChange, syncGroupToUrl]);

  // 页面刷新时恢复状态 - 增强版本
  useEffect(() => {
    const handlePageLoad = () => {
      if (groups.length > 0) {
        restoreGroupFromUrl();
      }
    };

    const handleBeforeUnload = () => {
      // 确保当前状态保存到URL
      if (selectedGroup && persistSelectedGroup) {
        const params = new URLSearchParams(window.location.search);
        params.set('group', selectedGroup.id.toString());
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState(null, '', newUrl);
      }
    };

    // 如果是首次加载且有群组数据
    if (groups.length > 0 && !selectedGroup) {
      handlePageLoad();
    }

    window.addEventListener('load', handlePageLoad);
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('load', handlePageLoad);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [groups, selectedGroup, restoreGroupFromUrl, persistSelectedGroup]);

  // 获取当前URL中的群组ID
  const getCurrentGroupId = () => {
    return searchParams.get('group');
  };

  // 清除群组选择
  const clearGroupSelection = useCallback(() => {
    selectGroup(null);
  }, [selectGroup]);

  // 导航到特定群组
  const navigateToGroup = useCallback((groupId: string | number) => {
    const group = groups.find(g => g.id.toString() === groupId.toString());
    if (group) {
      selectGroup(group);
    } else {
      console.warn('未找到群组:', groupId);
    }
  }, [groups, selectGroup]);

  return {
    // 状态
    selectedGroup,
    groups,
    messages,
    
    // 操作方法
    selectGroup,
    clearGroupSelection,
    navigateToGroup,
    getCurrentGroupId,
    setMessages, // 新增：暴露消息更新方法
    
    // 工具方法
    restoreGroupFromUrl,
    syncGroupToUrl,
  };
};

/**
 * 聊天界面专用的群组导航 Hook
 */
export const useChatGroupNavigation = () => {
  return useGroupNavigation({
    autoLoadMessages: true,
    persistSelectedGroup: true,
    syncOnGroupChange: true
  });
};