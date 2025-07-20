// 检测文本中的Telegram链接
export const detectTelegramLinks = (text: string): { url: string; text: string }[] => {
  const telegramLinkRegex = /https?:\/\/t\.me\/[^\s]+/gi;
  const matches = text.match(telegramLinkRegex);
  
  if (!matches) return [];
  
  return matches.map(url => ({
    url: url.trim(),
    text: url.trim()
  }));
};

// 检查是否为Telegram链接
export const isTelegramLink = (url: string): boolean => {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname === 't.me';
  } catch {
    return false;
  }
};

// 提取链接类型
export const getTelegramLinkType = (url: string): 'group' | 'channel' | 'user' | 'message' | 'sticker' | 'language' | 'unknown' => {
  try {
    const urlObj = new URL(url);
    if (urlObj.hostname !== 't.me') return 'unknown';
    
    const path = urlObj.pathname;
    
    if (path.startsWith('/setlanguage/')) return 'language';
    if (path.startsWith('/+')) return 'group'; // 私有群组邀请链接
    if (path.includes('/')) {
      const segments = path.split('/').filter(Boolean);
      if (segments.length === 1) return 'group'; // 公开群组或频道
      if (segments.length === 2 && !isNaN(Number(segments[1]))) return 'message'; // 消息链接
    }
    
    return 'unknown';
  } catch {
    return 'unknown';
  }
};

// 解析Telegram用户名或邀请码
export const parseTelegramIdentifier = (url: string): { type: 'username' | 'invite', value: string } | null => {
  try {
    const urlObj = new URL(url);
    const path = urlObj.pathname;
    
    if (path.startsWith('/+')) {
      // 私有群组邀请链接
      return {
        type: 'invite',
        value: path.substring(2)
      };
    } else if (path.length > 1) {
      // 公开群组/频道
      const username = path.substring(1).split('/')[0];
      return {
        type: 'username',
        value: username
      };
    }
    
    return null;
  } catch {
    return null;
  }
};

// 格式化成员数量
export const formatMemberCount = (count: number): string => {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`;
  } else if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
};

// 生成群组头像URL（如果没有自定义头像）
export const generateGroupAvatarUrl = (groupName: string): string => {
  // 这里可以实现一个基于群组名称的头像生成逻辑
  // 或者返回默认头像URL
  const firstChar = groupName.charAt(0).toUpperCase();
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(firstChar)}&background=0088cc&color=fff&size=128`;
};

// 截断描述文本
export const truncateDescription = (description: string, maxLength: number = 100): string => {
  if (description.length <= maxLength) return description;
  return description.substring(0, maxLength).trim() + '...';
};