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

// 检测文本中的群组信息（包括非链接格式）
export const detectGroupMentions = (text: string): { type: 'link' | 'username' | 'id' | 'name', value: string, text: string }[] => {
  const results: { type: 'link' | 'username' | 'id' | 'name', value: string, text: string }[] = [];
  
  // 1. 检测完整链接
  const linkMatches = text.match(/https?:\/\/t\.me\/[^\s]+/gi);
  if (linkMatches) {
    linkMatches.forEach(link => {
      results.push({
        type: 'link',
        value: link.trim(),
        text: link.trim()
      });
    });
  }
  
  // 2. 检测 @username 格式
  const usernameMatches = text.match(/@([a-zA-Z0-9_]{5,32})\b/g);
  if (usernameMatches) {
    usernameMatches.forEach(match => {
      const username = match.substring(1); // 移除 @
      results.push({
        type: 'username',
        value: username,
        text: match
      });
    });
  }
  
  // 3. 检测群组ID格式 (-100开头的数字)
  const groupIdMatches = text.match(/-100\d{10,}/g);
  if (groupIdMatches) {
    groupIdMatches.forEach(match => {
      results.push({
        type: 'id',
        value: match,
        text: match
      });
    });
  }
  
  // 4. 检测可能的群组名称（中文、英文群组名）
  // 匹配类似 "加入xxx群" "xxx群组" "xxx频道" 的格式
  const groupNamePatterns = [
    /(?:加入|进入|关注)?\s*([^\s]{2,20})\s*(?:群|群组|频道|社区|讨论组)/g,
    /([^\s]{2,20})\s*(?:官方群|交流群|学习群|技术群|资源群)/g,
    /(?:群组|频道|社区)[:：]\s*([^\s]{2,20})/g
  ];
  
  groupNamePatterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const groupName = match[1].trim();
      // 避免匹配到URL或其他已识别的内容
      if (!groupName.includes('http') && !groupName.includes('@') && !groupName.match(/^\d+$/)) {
        results.push({
          type: 'name',
          value: groupName,
          text: match[0]
        });
      }
    }
  });
  
  // 去重和过滤
  const unique = results.filter((item, index, self) => 
    index === self.findIndex(t => t.value === item.value && t.type === item.type)
  );
  
  return unique;
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