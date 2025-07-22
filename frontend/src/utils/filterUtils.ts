import { MessageFilter, MessageAPIFilter } from '../types/chat';

/**
 * 筛选条件转换工具函数
 * 负责在前端筛选格式和后端API格式之间转换
 */

/**
 * 将前端筛选条件转换为后端API参数格式
 * @param filter 前端筛选条件
 * @param pagination 分页参数
 * @returns 后端API参数格式
 */
export const convertFilterToAPIParams = (
  filter: MessageFilter, 
  pagination?: { skip?: number; limit?: number }
): MessageAPIFilter => {
  const apiFilter: MessageAPIFilter = {};

  // 复制基本字段
  if (filter.search?.trim()) {
    apiFilter.search = filter.search.trim();
  }

  if (filter.sender_username?.trim()) {
    apiFilter.sender_username = filter.sender_username.trim();
  }

  if (filter.media_type) {
    apiFilter.media_type = filter.media_type;
  }

  if (filter.has_media !== undefined) {
    apiFilter.has_media = filter.has_media;
  }

  if (filter.is_forwarded !== undefined) {
    apiFilter.is_forwarded = filter.is_forwarded;
  }

  if (filter.is_pinned !== undefined) {
    apiFilter.is_pinned = filter.is_pinned;
  }

  // 转换日期范围格式
  if (filter.date_range && filter.date_range.length === 2) {
    apiFilter.start_date = filter.date_range[0];
    apiFilter.end_date = filter.date_range[1];
  }

  // 添加分页参数
  if (pagination) {
    if (pagination.skip !== undefined) {
      apiFilter.skip = pagination.skip;
    }
    if (pagination.limit !== undefined) {
      apiFilter.limit = pagination.limit;
    }
  }

  return apiFilter;
};

/**
 * 将后端API参数转换为前端筛选条件格式
 * @param apiFilter 后端API参数
 * @returns 前端筛选条件
 */
export const convertAPIParamsToFilter = (apiFilter: MessageAPIFilter): MessageFilter => {
  const filter: MessageFilter = {};

  // 复制基本字段
  if (apiFilter.search) {
    filter.search = apiFilter.search;
  }

  if (apiFilter.sender_username) {
    filter.sender_username = apiFilter.sender_username;
  }

  if (apiFilter.media_type) {
    filter.media_type = apiFilter.media_type;
  }

  if (apiFilter.has_media !== undefined) {
    filter.has_media = apiFilter.has_media;
  }

  if (apiFilter.is_forwarded !== undefined) {
    filter.is_forwarded = apiFilter.is_forwarded;
  }

  if (apiFilter.is_pinned !== undefined) {
    filter.is_pinned = apiFilter.is_pinned;
  }

  // 转换日期格式
  if (apiFilter.start_date && apiFilter.end_date) {
    filter.date_range = [apiFilter.start_date, apiFilter.end_date];
  }

  return filter;
};

/**
 * 检查筛选条件是否为空
 * @param filter 筛选条件
 * @returns 是否为空筛选条件
 */
export const isEmptyFilter = (filter: MessageFilter): boolean => {
  return !filter.search &&
         !filter.sender_username &&
         !filter.media_type &&
         filter.has_media === undefined &&
         filter.is_forwarded === undefined &&
         filter.is_pinned === undefined &&
         (!filter.date_range || filter.date_range.length < 2);
};

/**
 * 获取筛选条件的可读描述
 * @param filter 筛选条件
 * @returns 筛选条件描述
 */
export const getFilterDescription = (filter: MessageFilter): string => {
  const descriptions: string[] = [];

  if (filter.search) {
    descriptions.push(`搜索: "${filter.search}"`);
  }

  if (filter.sender_username) {
    descriptions.push(`发送者: @${filter.sender_username}`);
  }

  if (filter.media_type) {
    const mediaTypeNames: Record<string, string> = {
      'photo': '图片',
      'video': '视频', 
      'document': '文档',
      'audio': '音频',
      'voice': '语音',
      'sticker': '贴纸'
    };
    descriptions.push(`类型: ${mediaTypeNames[filter.media_type] || filter.media_type}`);
  }

  if (filter.has_media === true) {
    descriptions.push('包含媒体');
  } else if (filter.has_media === false) {
    descriptions.push('仅文本');
  }

  if (filter.is_forwarded === true) {
    descriptions.push('转发消息');
  } else if (filter.is_forwarded === false) {
    descriptions.push('原创消息');
  }

  if (filter.is_pinned === true) {
    descriptions.push('置顶消息');
  }

  if (filter.date_range && filter.date_range.length === 2) {
    const startDate = new Date(filter.date_range[0]).toLocaleDateString();
    const endDate = new Date(filter.date_range[1]).toLocaleDateString();
    descriptions.push(`时间: ${startDate} - ${endDate}`);
  }

  return descriptions.length > 0 ? descriptions.join(', ') : '无筛选条件';
};

/**
 * 合并筛选条件
 * @param baseFilter 基础筛选条件
 * @param newFilter 新的筛选条件
 * @returns 合并后的筛选条件
 */
export const mergeFilters = (baseFilter: MessageFilter, newFilter: MessageFilter): MessageFilter => {
  return {
    ...baseFilter,
    ...newFilter,
    // 特殊处理日期范围
    date_range: newFilter.date_range || baseFilter.date_range
  };
};

/**
 * 清空筛选条件
 * @returns 空的筛选条件对象
 */
export const clearFilter = (): MessageFilter => {
  return {};
};

/**
 * 验证筛选条件是否有效
 * @param filter 筛选条件
 * @returns 验证结果 { valid: boolean, errors: string[] }
 */
export const validateFilter = (filter: MessageFilter): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];

  // 验证日期范围
  if (filter.date_range && filter.date_range.length === 2) {
    const startDate = new Date(filter.date_range[0]);
    const endDate = new Date(filter.date_range[1]);
    
    if (isNaN(startDate.getTime())) {
      errors.push('开始日期格式无效');
    }
    
    if (isNaN(endDate.getTime())) {
      errors.push('结束日期格式无效');
    }
    
    if (startDate.getTime() > endDate.getTime()) {
      errors.push('开始日期不能晚于结束日期');
    }
  }

  // 验证媒体类型
  if (filter.media_type) {
    const validMediaTypes = ['photo', 'video', 'document', 'audio', 'voice', 'sticker'];
    if (!validMediaTypes.includes(filter.media_type)) {
      errors.push('无效的媒体类型');
    }
  }

  // 验证发送者用户名（移除@符号）
  if (filter.sender_username) {
    const cleanUsername = filter.sender_username.replace(/^@/, '').trim();
    if (cleanUsername.length === 0) {
      errors.push('发送者用户名不能为空');
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
};