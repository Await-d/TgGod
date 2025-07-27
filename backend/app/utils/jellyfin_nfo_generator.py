"""
Jellyfin NFO 文件生成器
用于生成符合 Kodi/Jellyfin 标准的元数据文件
"""

import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import re
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from ..models.telegram import TelegramMessage, TelegramGroup
import logging

logger = logging.getLogger(__name__)

class JellyfinNFOGenerator:
    """Jellyfin NFO 文件生成器"""
    
    def __init__(self):
        # XML 非法字符的正则表达式
        self.xml_illegal_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')
        
    def sanitize_xml_text(self, text: str) -> str:
        """清理文本中的非法XML字符"""
        if not text:
            return ""
        
        # 移除XML非法字符
        cleaned = self.xml_illegal_chars.sub('', str(text))
        
        # 转义XML特殊字符
        cleaned = cleaned.replace('&', '&amp;')
        cleaned = cleaned.replace('<', '&lt;')
        cleaned = cleaned.replace('>', '&gt;')
        cleaned = cleaned.replace('"', '&quot;')
        cleaned = cleaned.replace("'", '&apos;')
        
        return cleaned.strip()
    
    def sanitize_filename(self, filename: str, max_length: int = 150) -> str:
        """清理文件名，移除非法字符"""
        if not filename:
            return "untitled"
        
        # 移除Windows/Unix非法字符
        illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
        cleaned = re.sub(illegal_chars, '_', filename)
        
        # 移除多余的空格和点
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = cleaned.strip('.')
        
        # 限制长度
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rsplit(' ', 1)[0]
        
        return cleaned or "untitled"
    
    def extract_video_duration(self, message: TelegramMessage) -> Optional[int]:
        """从消息中提取视频时长（分钟）"""
        try:
            # 如果媒体类型是video且有时长信息，可以从这里提取
            # 这里需要根据实际的媒体信息结构来实现
            # 暂时返回None，实际实现时需要解析媒体元数据
            return None
        except Exception as e:
            logger.warning(f"提取视频时长失败: {e}")
            return None
    
    def generate_movie_nfo(self, 
                          message: TelegramMessage, 
                          group: TelegramGroup,
                          task: 'DownloadTask' = None,
                          video_title: str = '',
                          video_file_path: str = '',
                          output_path: str = '') -> bool:
        """
        生成电影类型的NFO文件
        
        Args:
            message: Telegram消息对象
            group: Telegram群组对象
            task: 下载任务对象（包含订阅名）
            video_title: 视频标题
            video_file_path: 视频文件路径
            output_path: NFO文件输出路径
        
        Returns:
            生成是否成功
        """
        try:
            # 创建根元素
            movie = ET.Element("movie")
            
            # 基本信息
            self._add_element(movie, "title", video_title)
            self._add_element(movie, "originaltitle", video_title)
            
            # 描述信息 - 改进版
            plot = self._generate_enhanced_plot(message, group, task)
            self._add_element(movie, "plot", plot)
            self._add_element(movie, "outline", plot[:200] + "..." if len(plot) > 200 else plot)
            
            # 日期信息
            message_date = message.date
            year = message_date.year if message_date else datetime.now().year
            self._add_element(movie, "year", str(year))
            
            if message_date:
                premiered = message_date.strftime("%Y-%m-%d")
                self._add_element(movie, "premiered", premiered)
                
                dateadded = message_date.strftime("%Y-%m-%d %H:%M:%S")
                self._add_element(movie, "dateadded", dateadded)
            
            # 分类和来源信息
            self._add_element(movie, "genre", "Telegram")
            # 优先使用订阅名作为工作室，否则使用群组名
            studio_name = task.name if task and task.name else group.title
            self._add_element(movie, "studio", studio_name)
            
            # 发送者信息
            if message.sender_name:
                self._add_element(movie, "director", message.sender_name)
            
            # 视频时长
            duration = self.extract_video_duration(message)
            if duration:
                self._add_element(movie, "runtime", str(duration))
            
            # 图片信息
            self._add_element(movie, "thumb", "poster.jpg")
            self._add_element(movie, "fanart", "fanart.jpg")
            
            # 来源信息
            source = ET.SubElement(movie, "source")
            self._add_element(source, "name", "Telegram")
            if group.username:
                self._add_element(source, "url", f"https://t.me/{group.username}")
            
            # Telegram特有信息
            telegram_info = ET.SubElement(movie, "telegram")
            self._add_element(telegram_info, "message_id", str(message.message_id))
            self._add_element(telegram_info, "sender_id", str(message.sender_id or ""))
            self._add_element(telegram_info, "sender_name", message.sender_name or "")
            self._add_element(telegram_info, "group_id", str(group.telegram_id))
            self._add_element(telegram_info, "group_name", group.title)
            
            # 转发信息
            if message.is_forwarded:
                forward_info = ET.SubElement(telegram_info, "forward_info")
                self._add_element(forward_info, "from", message.forwarded_from or "")
                if message.forwarded_date:
                    self._add_element(forward_info, "date", message.forwarded_date.strftime("%Y-%m-%d"))
            
            # 媒体信息
            if message.media_size:
                fileinfo = ET.SubElement(movie, "fileinfo")
                streamdetails = ET.SubElement(fileinfo, "streamdetails")
                video_stream = ET.SubElement(streamdetails, "video")
                # 这里可以添加更多视频流信息
                self._add_element(video_stream, "codec", "unknown")
            
            # 保存NFO文件
            return self._save_nfo(movie, output_path)
            
        except Exception as e:
            logger.error(f"生成电影NFO失败: {e}")
            return False
    
    def generate_tvshow_nfo(self, 
                           group: TelegramGroup,
                           task: 'DownloadTask' = None,
                           series_title: str = '',
                           output_path: str = '') -> bool:
        """
        生成电视剧系列的NFO文件
        
        Args:
            group: Telegram群组对象
            task: 下载任务对象（包含订阅名）
            series_title: 系列标题
            output_path: NFO文件输出路径
        
        Returns:
            生成是否成功
        """
        try:
            # 创建根元素
            tvshow = ET.Element("tvshow")
            
            # 基本信息
            self._add_element(tvshow, "title", series_title)
            self._add_element(tvshow, "showtitle", series_title)
            
            # 描述信息
            plot = f"来自 Telegram 群组 {group.title} 的系列内容"
            self._add_element(tvshow, "plot", plot)
            
            # 分类信息
            self._add_element(tvshow, "genre", "Telegram")
            # 优先使用订阅名作为工作室，否则使用群组名
            studio_name = task.name if task and task.name else group.title
            self._add_element(tvshow, "studio", studio_name)
            
            # 状态信息
            self._add_element(tvshow, "status", "Continuing")
            
            # 图片信息
            self._add_element(tvshow, "thumb", "poster.jpg")
            self._add_element(tvshow, "fanart", "fanart.jpg")
            
            # Telegram信息
            telegram_info = ET.SubElement(tvshow, "telegram")
            self._add_element(telegram_info, "group_id", str(group.telegram_id))
            self._add_element(telegram_info, "group_name", group.title)
            if group.username:
                self._add_element(telegram_info, "username", group.username)
            
            # 保存NFO文件
            return self._save_nfo(tvshow, output_path)
            
        except Exception as e:
            logger.error(f"生成电视剧NFO失败: {e}")
            return False
    
    def generate_episode_nfo(self,
                            message: TelegramMessage,
                            group: TelegramGroup,
                            task: 'DownloadTask' = None,
                            episode_title: str = '',
                            season: int = 1,
                            episode: int = 1,
                            output_path: str = '') -> bool:
        """
        生成剧集NFO文件
        
        Args:
            message: Telegram消息对象
            group: Telegram群组对象
            episode_title: 剧集标题
            season: 季数
            episode: 集数
            output_path: NFO文件输出路径
        
        Returns:
            生成是否成功
        """
        try:
            # 创建根元素
            episode_elem = ET.Element("episodedetails")
            
            # 基本信息
            self._add_element(episode_elem, "title", episode_title)
            self._add_element(episode_elem, "season", str(season))
            self._add_element(episode_elem, "episode", str(episode))
            
            # 描述信息
            plot = message.text or f"来自 {group.title} 的剧集内容"
            self._add_element(episode_elem, "plot", plot)
            
            # 日期信息
            if message.date:
                aired = message.date.strftime("%Y-%m-%d")
                self._add_element(episode_elem, "aired", aired)
            
            # 发送者信息
            if message.sender_name:
                self._add_element(episode_elem, "director", message.sender_name)
            
            # 视频时长
            duration = self.extract_video_duration(message)
            if duration:
                self._add_element(episode_elem, "runtime", str(duration))
            
            # 图片信息
            self._add_element(episode_elem, "thumb", "thumb.jpg")
            
            # Telegram信息
            telegram_info = ET.SubElement(episode_elem, "telegram")
            self._add_element(telegram_info, "message_id", str(message.message_id))
            self._add_element(telegram_info, "group_id", str(group.telegram_id))
            
            # 保存NFO文件
            return self._save_nfo(episode_elem, output_path)
            
        except Exception as e:
            logger.error(f"生成剧集NFO失败: {e}")
            return False
    
    def _add_element(self, parent: ET.Element, tag: str, text: str):
        """安全地添加XML元素"""
        if text is not None:
            element = ET.SubElement(parent, tag)
            element.text = self.sanitize_xml_text(str(text))
    
    def _save_nfo(self, root: ET.Element, output_path: str) -> bool:
        """保存NFO文件"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 生成格式化的XML
            rough_string = ET.tostring(root, encoding='utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ", encoding='utf-8')
            
            # 移除空行
            lines = [line for line in pretty_xml.decode('utf-8').split('\n') if line.strip()]
            formatted_xml = '\n'.join(lines)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_xml)
            
            logger.info(f"NFO文件生成成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存NFO文件失败: {e}")
            return False
    
    def _generate_enhanced_plot(self, message: TelegramMessage, group: TelegramGroup, task: 'DownloadTask' = None) -> str:
        """生成增强的剧情描述"""
        plot_parts = []
        
        # 如果有消息文本，作为主要描述
        if message.text and message.text.strip():
            plot_parts.append(message.text.strip())
        
        # 添加来源信息
        source_info = []
        if task and task.name:
            source_info.append(f"订阅: {task.name}")
        
        source_info.append(f"群组: {group.title}")
        
        if message.sender_name:
            source_info.append(f"发送者: {message.sender_name}")
        
        if message.date:
            date_str = message.date.strftime("%Y年%m月%d日")
            source_info.append(f"发布时间: {date_str}")
        
        # 添加媒体信息
        media_info = []
        if message.media_type:
            type_names = {
                'video': '视频',
                'photo': '图片', 
                'audio': '音频',
                'document': '文档',
                'voice': '语音',
                'sticker': '贴纸'
            }
            media_info.append(f"类型: {type_names.get(message.media_type, message.media_type)}")
        
        if message.media_size:
            size_mb = message.media_size / (1024 * 1024)
            if size_mb >= 1024:
                size_str = f"{size_mb/1024:.1f} GB"
            else:
                size_str = f"{size_mb:.1f} MB"
            media_info.append(f"大小: {size_str}")
        
        # 组合描述
        if not plot_parts and not source_info:
            return f"来自 {group.title} 的媒体内容"
        
        result = []
        if plot_parts:
            result.extend(plot_parts)
        
        if source_info:
            result.append("\n来源信息:")
            result.append(" | ".join(source_info))
            
        if media_info:
            result.append("\n媒体信息:")
            result.append(" | ".join(media_info))
        
        return "\n".join(result)

class JellyfinPathManager:
    """Jellyfin 路径管理器"""
    
    def __init__(self):
        self.nfo_generator = JellyfinNFOGenerator()
    
    def generate_media_path(self, 
                           base_path: str,
                           group: TelegramGroup, 
                           message: TelegramMessage,
                           task: 'DownloadTask' = None,
                           rule: 'FilterRule' = None,
                           use_series_structure: bool = False) -> Dict[str, str]:
        """
        生成Jellyfin兼容的媒体路径结构
        
        Args:
            base_path: 基础下载路径
            group: Telegram群组
            message: Telegram消息
            task: 下载任务（包含订阅名）
            rule: 过滤规则（包含关键词）
            use_series_structure: 是否使用剧集结构
        
        Returns:
            包含各种路径的字典
        """
        try:
            # 优先使用规则的触发关键词作为文件夹名
            folder_name = self._generate_folder_name_from_keywords(rule, task, group)
            
            # 生成视频标题
            video_title = self._generate_video_title(message)
            
            # 生成日期字符串
            date_str = message.date.strftime("%Y-%m-%d") if message.date else datetime.now().strftime("%Y-%m-%d")
            
            # 生成目录名
            if use_series_structure:
                # 剧集结构: [关键词]/Season 01/
                series_dir = os.path.join(base_path, folder_name)
                season_dir = os.path.join(series_dir, "Season 01")  # 默认第一季
                episode_dir = season_dir
                video_filename = f"S01E{message.message_id:06d} - {video_title}"
            else:
                # 电影结构: [关键词]/[视频标题 - 日期]/
                video_dir_name = f"{video_title} - {date_str}"
                video_dir_name = self.nfo_generator.sanitize_filename(video_dir_name, 150)
                episode_dir = os.path.join(base_path, folder_name, video_dir_name)
                video_filename = video_title
            
            # 清理文件名
            video_filename = self.nfo_generator.sanitize_filename(video_filename, 100)
            
            return {
                'base_path': base_path,
                'keyword_dir': os.path.join(base_path, folder_name),
                'episode_dir': episode_dir,
                'video_filename': video_filename,
                'video_title': video_title,
                'date_str': date_str,
                'folder_name': folder_name,
                'group_name': group.title,  # 保留原始群组名用于NFO元数据
                'keywords': rule.keywords if rule else []  # 保留关键词信息
            }
            
        except Exception as e:
            logger.error(f"生成媒体路径失败: {e}")
            return {}
    
    def _generate_video_title(self, message: TelegramMessage) -> str:
        """生成视频标题 - 改进版"""
        # 优先使用媒体文件名
        if message.media_filename:
            title = os.path.splitext(message.media_filename)[0]
            # 移除常见的文件编号后缀
            title = self._clean_filename_title(title)
            return self.nfo_generator.sanitize_filename(title, 100)
        
        # 其次使用消息文本，但进行智能提取
        if message.text:
            title = self._extract_title_from_text(message.text.strip())
            return self.nfo_generator.sanitize_filename(title, 100)
        
        # 最后使用消息ID和日期
        date_str = message.date.strftime("%Y%m%d") if message.date else "unknown"
        return f"Media_{date_str}_{message.message_id}"
    
    def _clean_filename_title(self, filename: str) -> str:
        """清理文件名标题，移除常见的编号和后缀"""
        import re
        
        # 移除常见的文件编号模式
        patterns = [
            r'_\d+$',           # 结尾的下划线+数字
            r'\(\d+\)$',        # 结尾的括号数字
            r'\[\d+\]$',        # 结尾的方括号数字
            r'\.part\d+$',      # .part文件后缀
            r'_[a-f0-9]{8,}$',  # 哈希值后缀
        ]
        
        cleaned = filename
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _extract_title_from_text(self, text: str) -> str:
        """从消息文本中智能提取标题"""
        # 如果文本很短，直接使用
        if len(text) <= 50:
            return text
        
        # 尝试找到第一行作为标题
        lines = text.split('\n')
        first_line = lines[0].strip()
        
        # 如果第一行合理长度，使用第一行
        if 10 <= len(first_line) <= 100:
            return first_line
        
        # 否则使用前50个字符并在合适的地方截断
        truncated = text[:80]
        # 尝试在标点符号处截断
        for punct in ['。', '！', '？', '.', '!', '?']:
            if punct in truncated:
                return truncated[:truncated.find(punct) + 1]
        
        # 尝试在空格处截断
        if ' ' in truncated:
            words = truncated.split(' ')
            result = ''
            for word in words:
                if len(result + word) <= 50:
                    result += word + ' '
                else:
                    break
            return result.strip()
        
        # 最后直接截断
        return truncated[:50] + "..."
    
    def _generate_folder_name_from_keywords(self, rule: 'FilterRule' = None, task: 'DownloadTask' = None, group: TelegramGroup = None) -> str:
        """根据规则关键词生成文件夹名称"""
        # 优先级: 规则关键词 > 任务名 > 群组名
        
        # 1. 尝试使用规则的第一个关键词
        if rule and rule.keywords and len(rule.keywords) > 0:
            # 如果有多个关键词，选择最合适的一个
            primary_keyword = self._select_primary_keyword(rule.keywords)
            return self.nfo_generator.sanitize_filename(primary_keyword, 50)
        
        # 2. 兜底使用任务名称
        if task and task.name:
            return self.nfo_generator.sanitize_filename(task.name, 50)
        
        # 3. 最后兜底使用群组名称
        if group and group.title:
            return self.nfo_generator.sanitize_filename(group.title, 50)
        
        # 4. 最后的兜底
        return "Unknown"
    
    def _select_primary_keyword(self, keywords: list) -> str:
        """从多个关键词中选择最合适的作为主要关键词"""
        if not keywords:
            return "Unknown"
        
        # 如果只有一个关键词，直接返回
        if len(keywords) == 1:
            return keywords[0]
        
        # 如果有多个关键词，选择策略：
        # 1. 优先选择最短的关键词（通常是主要名称）
        # 2. 避免选择过长的关键词
        # 3. 优先选择中文关键词
        
        suitable_keywords = []
        for keyword in keywords:
            # 过滤掉过长的关键词
            if len(keyword) <= 20:
                suitable_keywords.append(keyword)
        
        if not suitable_keywords:
            suitable_keywords = keywords
        
        # 按长度排序，优先选择较短的
        suitable_keywords.sort(key=len)
        
        # 优先选择包含中文字符的关键词
        for keyword in suitable_keywords:
            if any('\u4e00' <= char <= '\u9fff' for char in keyword):
                return keyword
        
        # 如果没有中文关键词，返回最短的
        return suitable_keywords[0]