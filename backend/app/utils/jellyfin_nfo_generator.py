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
                          video_title: str,
                          video_file_path: str,
                          output_path: str) -> bool:
        """
        生成电影类型的NFO文件
        
        Args:
            message: Telegram消息对象
            group: Telegram群组对象
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
            
            # 描述信息
            plot = message.text or f"来自 {group.title} 的媒体内容"
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
            self._add_element(movie, "studio", group.title)
            
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
                           series_title: str,
                           output_path: str) -> bool:
        """
        生成电视剧系列的NFO文件
        
        Args:
            group: Telegram群组对象
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
            self._add_element(tvshow, "studio", group.title)
            
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
                            episode_title: str,
                            season: int,
                            episode: int,
                            output_path: str) -> bool:
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

class JellyfinPathManager:
    """Jellyfin 路径管理器"""
    
    def __init__(self):
        self.nfo_generator = JellyfinNFOGenerator()
    
    def generate_media_path(self, 
                           base_path: str,
                           group: TelegramGroup, 
                           message: TelegramMessage,
                           use_series_structure: bool = False) -> Dict[str, str]:
        """
        生成Jellyfin兼容的媒体路径结构
        
        Args:
            base_path: 基础下载路径
            group: Telegram群组
            message: Telegram消息
            use_series_structure: 是否使用剧集结构
        
        Returns:
            包含各种路径的字典
        """
        try:
            # 清理群组名称
            group_name = self.nfo_generator.sanitize_filename(group.title, 100)
            
            # 生成视频标题
            video_title = self._generate_video_title(message)
            
            # 生成日期字符串
            date_str = message.date.strftime("%Y-%m-%d") if message.date else datetime.now().strftime("%Y-%m-%d")
            
            # 生成目录名
            if use_series_structure:
                # 剧集结构: [群组名]/Season 01/
                series_dir = os.path.join(base_path, group_name)
                season_dir = os.path.join(series_dir, "Season 01")  # 默认第一季
                episode_dir = season_dir
                video_filename = f"S01E{message.message_id:06d} - {video_title}"
            else:
                # 电影结构: [群组名]/[视频标题 - 日期]/
                video_dir_name = f"{video_title} - {date_str}"
                video_dir_name = self.nfo_generator.sanitize_filename(video_dir_name, 150)
                episode_dir = os.path.join(base_path, group_name, video_dir_name)
                video_filename = video_title
            
            # 清理文件名
            video_filename = self.nfo_generator.sanitize_filename(video_filename, 100)
            
            return {
                'base_path': base_path,
                'group_dir': os.path.join(base_path, group_name),
                'episode_dir': episode_dir,
                'video_filename': video_filename,
                'video_title': video_title,
                'date_str': date_str,
                'group_name': group_name
            }
            
        except Exception as e:
            logger.error(f"生成媒体路径失败: {e}")
            return {}
    
    def _generate_video_title(self, message: TelegramMessage) -> str:
        """生成视频标题"""
        # 优先使用媒体文件名
        if message.media_filename:
            title = os.path.splitext(message.media_filename)[0]
            return self.nfo_generator.sanitize_filename(title, 100)
        
        # 其次使用消息文本的前50个字符
        if message.text:
            title = message.text.strip()[:50]
            return self.nfo_generator.sanitize_filename(title, 100)
        
        # 最后使用消息ID
        return f"Media_{message.message_id}"