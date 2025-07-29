"""
文件组织服务
处理下载文件的整理、去重和目录结构组织
"""
import os
import shutil
import hashlib
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class FileOrganizerService:
    """文件组织服务，负责下载文件的整理和去重"""
    
    def __init__(self):
        self.hash_cache: Dict[str, str] = {}  # 文件哈希缓存
        self.duplicate_files: List[str] = []  # 重复文件记录
    
    def calculate_file_hash(self, file_path: str, chunk_size: int = 8192) -> Optional[str]:
        """
        计算文件的SHA256哈希值
        
        Args:
            file_path: 文件路径
            chunk_size: 读取块大小
            
        Returns:
            文件哈希值，如果失败返回None
        """
        try:
            if not os.path.exists(file_path):
                return None
                
            # 检查缓存
            file_stat = os.stat(file_path)
            cache_key = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}"
            if cache_key in self.hash_cache:
                return self.hash_cache[cache_key]
            
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_sha256.update(chunk)
            
            file_hash = hash_sha256.hexdigest()
            self.hash_cache[cache_key] = file_hash
            return file_hash
            
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return None
    
    def check_duplicate_by_hash(self, file_path: str, target_dir: str) -> Optional[str]:
        """
        通过哈希值检查文件是否重复
        
        Args:
            file_path: 待检查的文件路径
            target_dir: 目标目录
            
        Returns:
            如果找到重复文件，返回重复文件路径；否则返回None
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            file_hash = self.calculate_file_hash(file_path)
            if not file_hash:
                return None
            
            # 遍历目标目录查找相同哈希的文件
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    existing_file_path = os.path.join(root, file)
                    if existing_file_path == file_path:
                        continue
                    
                    existing_hash = self.calculate_file_hash(existing_file_path)
                    if existing_hash == file_hash:
                        logger.info(f"发现重复文件: {file_path} <-> {existing_file_path}")
                        return existing_file_path
            
            return None
            
        except Exception as e:
            logger.error(f"检查重复文件失败 {file_path}: {e}")
            return None
    
    def generate_organized_path(self, 
                              message: Any, 
                              task_data: Dict[str, Any], 
                              original_filename: str) -> str:
        """
        根据任务配置生成组织后的文件路径
        
        Args:
            message: 消息对象
            task_data: 任务数据
            original_filename: 原始文件名
            
        Returns:
            组织后的文件路径
        """
        try:
            base_path = task_data.get('download_path', '/downloads')
            
            # 调试日志：确认路径生成逻辑
            logger.info(f"生成组织路径 - use_jellyfin_structure: {task_data.get('use_jellyfin_structure', False)}")
            logger.info(f"生成组织路径 - base_path: {base_path}")
            logger.info(f"生成组织路径 - original_filename: {original_filename}")
            
            # 如果启用了Jellyfin结构，交给Jellyfin服务处理
            if task_data.get('use_jellyfin_structure', False):
                jellyfin_path = self._generate_jellyfin_path(message, task_data, original_filename)
                logger.info(f"生成Jellyfin路径: {jellyfin_path}")
                return jellyfin_path
            
            # 标准文件组织
            return self._generate_standard_path(message, task_data, original_filename)
            
        except Exception as e:
            logger.error(f"生成组织路径失败: {e}")
            # 回退到基本路径
            return os.path.join(task_data.get('download_path', '/downloads'), original_filename)
    
    def _generate_standard_path(self, 
                               message: Any, 
                               task_data: Dict[str, Any], 
                               original_filename: str) -> str:
        """
        生成标准的文件组织路径
        
        Args:
            message: 消息对象
            task_data: 任务数据
            original_filename: 原始文件名
            
        Returns:
            标准组织的文件路径
        """
        base_path = task_data.get('download_path', '/downloads')
        
        # 获取匹配的关键字，优先使用触发下载的关键字，否则使用规则名称
        matched_keyword = task_data.get('matched_keyword')
        if matched_keyword:
            rule_name = matched_keyword
            logger.info(f"使用匹配关键字作为规则名: {matched_keyword}")
        else:
            rule_name = task_data.get('rule_name', 'Unknown_Rule')
            logger.info(f"使用规则名称: {rule_name}")
        
        # 清理规则名称，移除文件系统不支持的字符
        safe_rule_name = self._sanitize_path_component(rule_name)
        
        # 根据是否按日期组织决定目录结构
        if task_data.get('organize_by_date', True):
            # 使用消息日期组织
            if hasattr(message, 'date') and message.date:
                date_obj = message.date
                if isinstance(date_obj, str):
                    # 如果是字符串，尝试解析
                    try:
                        date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
                    except:
                        date_obj = datetime.now()
            else:
                # 使用当天日期
                date_obj = datetime.now()
            
            # 生成视频标题
            video_title = self._extract_video_title(message, original_filename)
            date_str = date_obj.strftime('%Y-%m-%d')
            
            # 生成目录名：[规则名] - [视频标题] - [YYYY-MM-DD]
            dir_name = f"{safe_rule_name} - {video_title} - {date_str}"
            safe_dir_name = self._sanitize_path_component(dir_name)
            
            # 生成文件名：[规则名] - [视频标题] - [YYYY-MM-DD].扩展名
            file_name_without_ext = os.path.splitext(original_filename)[0]
            file_ext = os.path.splitext(original_filename)[1]
            new_filename = f"{safe_rule_name} - {video_title} - {date_str}{file_ext}"
            safe_filename = self._sanitize_filename(new_filename)
            
            # 标准格式：base_path/规则名/[规则名] - [视频标题] - [YYYY-MM-DD]/[规则名] - [视频标题] - [YYYY-MM-DD].扩展名
            organized_path = os.path.join(base_path, safe_rule_name, safe_dir_name, safe_filename)
        else:
            # 不按日期组织，使用规则名：base_path/规则名/原文件名
            organized_path = os.path.join(base_path, safe_rule_name, original_filename)
        
        return organized_path
    
    def _generate_jellyfin_path(self, 
                               message: Any, 
                               task_data: Dict[str, Any], 
                               original_filename: str) -> str:
        """
        生成Jellyfin格式的文件组织路径
        
        Args:
            message: 消息对象
            task_data: 任务数据
            original_filename: 原始文件名
            
        Returns:
            Jellyfin格式的文件路径
        """
        base_path = task_data.get('download_path', '/downloads')
        
        # 获取订阅名作为系列名（优先使用订阅名，回退到群组名）
        subscription_name = task_data.get('subscription_name') or task_data.get('task_name') or task_data.get('group_name', 'Unknown_Subscription')
        # 清理路径组件中的非法字符
        safe_subscription_name = self._sanitize_path_component(subscription_name)
        
        logger.info(f"Jellyfin路径生成 - subscription_name: {subscription_name}")
        logger.info(f"Jellyfin路径生成 - safe_subscription_name: {safe_subscription_name}")
        logger.info(f"Jellyfin路径生成 - use_series_structure: {task_data.get('use_series_structure', False)}")
        
        # 如果启用了系列结构
        if task_data.get('use_series_structure', False):
            # 使用 Series/Season/Episode 结构
            if hasattr(message, 'date') and message.date:
                date_obj = message.date
                if isinstance(date_obj, str):
                    try:
                        date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
                    except:
                        date_obj = datetime.now()
                
                season = date_obj.strftime('%Y')  # 年份作为季
                episode = f"E{message.message_id:06d}"  # 消息ID作为集数
                
                jellyfin_path = os.path.join(
                    base_path,
                    safe_subscription_name,
                    f"Season {season}",
                    f"{safe_subscription_name} - S{season}{episode} - {self._sanitize_filename(original_filename)}"
                )
            else:
                # 无日期信息，使用简单结构
                jellyfin_path = os.path.join(
                    base_path,
                    safe_subscription_name,
                    f"{safe_subscription_name} - {self._sanitize_filename(original_filename)}"
                )
        else:
            # 使用Movies结构（按年份分组）
            if hasattr(message, 'date') and message.date:
                date_obj = message.date
                if isinstance(date_obj, str):
                    try:
                        date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
                    except:
                        date_obj = datetime.now()
                
                year = date_obj.strftime('%Y')
                movie_folder = f"{safe_subscription_name} ({year})"
                
                jellyfin_path = os.path.join(
                    base_path,
                    movie_folder,
                    self._sanitize_filename(original_filename)
                )
            else:
                # 无日期信息
                movie_folder = safe_subscription_name
                jellyfin_path = os.path.join(
                    base_path,
                    movie_folder,
                    self._sanitize_filename(original_filename)
                )
        
        return jellyfin_path
    
    def _sanitize_filename(self, filename: str, max_length: int = None) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            max_length: 最大文件名长度
            
        Returns:
            清理后的文件名
        """
        if not filename:
            return "unknown"
        
        # 移除或替换非法字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        clean_name = filename
        for char in illegal_chars:
            clean_name = clean_name.replace(char, '_')
        
        # 移除多余的空格和点
        clean_name = ' '.join(clean_name.split())
        clean_name = clean_name.strip('. ')
        
        # 限制长度
        if max_length and len(clean_name) > max_length:
            name, ext = os.path.splitext(clean_name)
            clean_name = name[:max_length-len(ext)] + ext
        
        return clean_name if clean_name else "unknown"
    
    def _sanitize_path_component(self, path_component: str, max_length: int = 100) -> str:
        """
        清理路径组件（如群组名称），移除文件系统不支持的字符
        
        Args:
            path_component: 原始路径组件
            max_length: 最大长度
            
        Returns:
            清理后的路径组件
        """
        if not path_component:
            return "Unknown"
        
        # 移除或替换文件系统不支持的字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '\n', '\r', '\t']
        clean_component = path_component
        for char in illegal_chars:
            clean_component = clean_component.replace(char, '_')
        
        # 移除多余的空格
        clean_component = ' '.join(clean_component.split())
        clean_component = clean_component.strip('. ')
        
        # 限制长度，避免过长的目录名
        if len(clean_component) > max_length:
            clean_component = clean_component[:max_length].rstrip()
        
        return clean_component if clean_component else "Unknown"
    
    def _extract_video_title(self, message: Any, original_filename: str) -> str:
        """
        从消息中提取视频标题
        
        Args:
            message: 消息对象
            original_filename: 原始文件名
            
        Returns:
            视频标题
        """
        import re
        
        # 优先使用消息文本作为标题
        if hasattr(message, 'text') and message.text:
            title = self._clean_and_extract_title(message.text)
            if title:
                return title
        
        # 其次使用消息说明
        if hasattr(message, 'caption') and message.caption:
            title = self._clean_and_extract_title(message.caption)
            if title:
                return title
        
        # 尝试从文件名中提取有意义的标题
        if original_filename:
            title = self._extract_title_from_filename(original_filename)
            if title:
                return title
        
        # 使用消息ID作为最后的标识
        if hasattr(message, 'message_id') and message.message_id:
            return str(message.message_id)
        
        # 默认标题
        return "Media"
    
    def _clean_and_extract_title(self, text: str) -> str:
        """
        从文本中清理和提取标题
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的标题
        """
        import re
        
        if not text:
            return ""
        
        # 移除前后空格
        text = text.strip()
        
        # 移除常见的无用前缀和后缀
        # 移除URL
        text = re.sub(r'https?://[^\s]+', '', text)
        # 移除邮箱
        text = re.sub(r'\S+@\S+', '', text)
        # 移除电话号码
        text = re.sub(r'[+]?[\d\-\(\)\s]{10,}', '', text)
        # 移除多余的空格
        text = ' '.join(text.split())
        
        # 尝试提取标题的几种模式
        patterns = [
            # 【标题】格式
            r'【([^】]+)】',
            # 《标题》格式
            r'《([^》]+)》',
            # "标题"格式
            r'"([^"]+)"',
            r'"([^"]+)"',
            # #标题# 格式
            r'#([^#]+)#',
            # 标题: 格式
            r'^([^:：]+)[：:]',
            # 如果是单行且不太长，直接使用
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group(1).strip()
                if len(title) > 3 and len(title) <= 80:  # 长度合理
                    return self._sanitize_title(title)
        
        # 如果没有匹配到特殊格式，尝试提取第一句话或第一行
        lines = text.split('\n')
        first_line = lines[0].strip()
        
        # 如果第一行长度合适，使用第一行
        if 3 <= len(first_line) <= 80:
            return self._sanitize_title(first_line)
        
        # 如果第一行太长，尝试提取前面的句子
        sentences = re.split(r'[。！？.!?]', first_line)
        if sentences and len(sentences[0].strip()) >= 3:
            title = sentences[0].strip()
            if len(title) <= 80:
                return self._sanitize_title(title)
            else:
                # 截取前50个字符
                return self._sanitize_title(title[:50] + "...")
        
        # 如果都不符合，截取前50个字符
        if len(text) > 50:
            return self._sanitize_title(text[:50] + "...")
        
        return self._sanitize_title(text) if text else ""
    
    def _extract_title_from_filename(self, filename: str) -> str:
        """
        从文件名中提取有意义的标题
        
        Args:
            filename: 原始文件名
            
        Returns:
            提取的标题
        """
        import re
        
        if not filename:
            return ""
        
        # 去除扩展名
        name_without_ext = os.path.splitext(filename)[0]
        
        # 移除常见的无用模式
        patterns_to_remove = [
            # 移除时间戳 (20231201_123456)
            r'\d{8}_\d{6}',
            # 移除纯数字ID (16956_82925)
            r'^\d+_\d+$',
            r'_\d+_\d+$',
            # 移除文件编号 [001], (001)
            r'\[\d+\]',
            r'\(\d+\)',
            # 移除常见后缀
            r'_final$', r'_copy$', r'_backup$',
            # 移除下划线和破折号的组合
            r'[-_]{2,}',
        ]
        
        clean_name = name_without_ext
        for pattern in patterns_to_remove:
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
        
        # 将下划线和破折号替换为空格
        clean_name = re.sub(r'[-_]', ' ', clean_name)
        # 移除多余空格
        clean_name = ' '.join(clean_name.split())
        
        # 如果清理后的名称太短或为空，使用原始文件名
        if len(clean_name.strip()) < 3:
            return self._sanitize_title(name_without_ext)
        
        return self._sanitize_title(clean_name.strip())
    
    def _sanitize_title(self, title: str) -> str:
        """
        清理标题中的特殊字符
        
        Args:
            title: 原始标题
            
        Returns:
            清理后的标题
        """
        if not title:
            return ""
        
        # 移除文件系统不支持的字符，但保留中文和常用标点
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '\n', '\r', '\t']
        clean_title = title
        for char in illegal_chars:
            clean_title = clean_title.replace(char, ' ')
        
        # 移除多余的空格
        clean_title = ' '.join(clean_title.split())
        clean_title = clean_title.strip()
        
        # 如果标题太长，智能截取
        if len(clean_title) > 60:
            # 尝试在标点符号处截断
            for i in range(50, min(60, len(clean_title))):
                if clean_title[i] in '，。！？,. ':
                    clean_title = clean_title[:i]
                    break
            else:
                clean_title = clean_title[:50] + "..."
        
        return clean_title if clean_title else "Media"
    
    def _generate_additional_media_files(self, 
                                        video_path: str, 
                                        message: Any, 
                                        task_data: Dict[str, Any]):
        """
        生成附加的媒体文件（NFO、封面图等）
        
        Args:
            video_path: 视频文件路径
            message: 消息对象
            task_data: 任务数据
        """
        try:
            # 检查文件是否为视频文件
            if not self._is_video_file(video_path):
                logger.debug(f"跳过非视频文件的媒体文件生成: {video_path}")
                return
            
            logger.info(f"开始为视频文件生成附加媒体文件: {video_path}")
            
            # 生成NFO元数据文件
            nfo_path = self.generate_nfo_file(video_path, message, task_data)
            if nfo_path:
                logger.info(f"NFO文件生成成功: {nfo_path}")
            
            # 生成图片文件（封面、背景图、缩略图）
            image_results = self.generate_media_images(video_path, message, task_data)
            
            for image_type, image_path in image_results.items():
                if image_path:
                    logger.info(f"{image_type}图片生成成功: {image_path}")
            
            # 记录生成的附加文件
            additional_files = []
            if nfo_path:
                additional_files.append(nfo_path)
            additional_files.extend([path for path in image_results.values() if path])
            
            if additional_files:
                logger.info(f"为视频 {os.path.basename(video_path)} 生成了 {len(additional_files)} 个附加文件")
            
        except Exception as e:
            logger.error(f"生成附加媒体文件失败: {e}")
    
    def _is_video_file(self, file_path: str) -> bool:
        """
        检查文件是否为视频文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为视频文件
        """
        video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ts', '.mts'}
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in video_extensions
    
    def organize_downloaded_file(self, 
                                source_path: str, 
                                message: Any, 
                                task_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        整理已下载的文件
        
        Args:
            source_path: 源文件路径
            message: 消息对象
            task_data: 任务数据
        
        Returns:
            (是否成功, 目标文件路径, 错误信息)
        """
        try:
            if not os.path.exists(source_path):
                return False, "", f"源文件不存在: {source_path}"
            
            # 获取原始文件名
            original_filename = os.path.basename(source_path)
            
            # 生成目标路径
            target_path = self.generate_organized_path(message, task_data, original_filename)
            
            # 如果已经在目标位置，无需移动
            if os.path.abspath(source_path) == os.path.abspath(target_path):
                logger.info(f"文件已在目标位置: {target_path}")
                return True, target_path, None
            
            # 检查是否有重复文件
            target_dir = os.path.dirname(target_path)
            duplicate_path = self.check_duplicate_by_hash(source_path, target_dir)
            
            if duplicate_path:
                # 发现重复文件，删除源文件
                logger.info(f"发现重复文件，删除源文件: {source_path}")
                try:
                    os.remove(source_path)
                    self.duplicate_files.append(source_path)
                except Exception as e:
                    logger.warning(f"删除重复文件失败: {e}")
                
                return True, duplicate_path, f"文件重复，使用现有文件: {duplicate_path}"
            
            # 创建目标目录
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # 移动文件到目标位置
            shutil.move(source_path, target_path)
            logger.info(f"文件已整理: {source_path} -> {target_path}")
            
            # 生成附加的媒体文件（NFO、封面图等）
            self._generate_additional_media_files(target_path, message, task_data)
            
            return True, target_path, None
            
        except Exception as e:
            error_msg = f"整理文件失败 {source_path}: {e}"
            logger.error(error_msg)
            return False, source_path, error_msg
    
    def get_organization_stats(self) -> Dict[str, Any]:
        """
        获取文件组织统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "hash_cache_size": len(self.hash_cache),
            "duplicate_files_count": len(self.duplicate_files),
            "duplicate_files": self.duplicate_files.copy()
        }
    
    def clear_cache(self):
        """清理缓存"""
        self.hash_cache.clear()
        self.duplicate_files.clear()
        logger.info("文件组织服务缓存已清理")
    
    def generate_nfo_file(self, 
                         video_path: str, 
                         message: Any, 
                         task_data: Dict[str, Any]) -> Optional[str]:
        """
        生成NFO元数据文件
        
        Args:
            video_path: 视频文件路径
            message: 消息对象
            task_data: 任务数据
            
        Returns:
            NFO文件路径，如果失败返回None
        """
        try:
            if not task_data.get('include_metadata', True):
                return None
            
            # 生成NFO文件路径
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            nfo_path = os.path.join(video_dir, f"{video_name}.nfo")
            
            # 提取视频信息
            video_info = self._extract_video_info(video_path)
            
            # 创建NFO XML结构
            root = ET.Element("movie")
            
            # 基本信息
            title_elem = ET.SubElement(root, "title")
            title_elem.text = self._extract_video_title(message, os.path.basename(video_path))
            
            plot_elem = ET.SubElement(root, "plot")
            plot_elem.text = self._extract_plot_from_message(message)
            
            # 日期信息
            if hasattr(message, 'date') and message.date:
                date_obj = message.date
                if isinstance(date_obj, str):
                    try:
                        date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
                    except:
                        date_obj = datetime.now()
                
                year_elem = ET.SubElement(root, "year")
                year_elem.text = str(date_obj.year)
                
                premiered_elem = ET.SubElement(root, "premiered")
                premiered_elem.text = date_obj.strftime('%Y-%m-%d')
                
                dateadded_elem = ET.SubElement(root, "dateadded")
                dateadded_elem.text = date_obj.strftime('%Y-%m-%d %H:%M:%S')
            
            # 分类和来源信息
            genre_elem = ET.SubElement(root, "genre")
            genre_elem.text = "Telegram"
            
            studio_elem = ET.SubElement(root, "studio")
            studio_elem.text = task_data.get('subscription_name') or task_data.get('group_name', 'Unknown')
            
            # 发送者信息
            if hasattr(message, 'from_user') and message.from_user:
                director_elem = ET.SubElement(root, "director")
                if hasattr(message.from_user, 'first_name'):
                    director_name = message.from_user.first_name
                    if hasattr(message.from_user, 'last_name') and message.from_user.last_name:
                        director_name += f" {message.from_user.last_name}"
                    director_elem.text = director_name
                elif hasattr(message.from_user, 'username'):
                    director_elem.text = message.from_user.username
            
            # 视频时长
            if video_info and video_info.get('format') and video_info['format'].get('duration'):
                runtime_elem = ET.SubElement(root, "runtime")
                runtime_elem.text = str(int(float(video_info['format']['duration']) / 60))  # 转换为分钟
            
            # 图片引用
            thumb_elem = ET.SubElement(root, "thumb")
            thumb_elem.text = "poster.jpg"
            
            fanart_elem = ET.SubElement(root, "fanart")
            fanart_elem.text = "fanart.jpg"
            
            # 来源信息
            source_elem = ET.SubElement(root, "source")
            source_name_elem = ET.SubElement(source_elem, "name")
            source_name_elem.text = "Telegram"
            
            # Telegram特定信息
            telegram_elem = ET.SubElement(root, "telegram")
            
            if hasattr(message, 'message_id'):
                msg_id_elem = ET.SubElement(telegram_elem, "message_id")
                msg_id_elem.text = str(message.message_id)
            
            if hasattr(message, 'from_user') and message.from_user:
                sender_id_elem = ET.SubElement(telegram_elem, "sender_id")
                sender_id_elem.text = str(message.from_user.id)
                
                sender_name_elem = ET.SubElement(telegram_elem, "sender_name")
                if hasattr(message.from_user, 'first_name'):
                    sender_name = message.from_user.first_name
                    if hasattr(message.from_user, 'last_name') and message.from_user.last_name:
                        sender_name += f" {message.from_user.last_name}"
                    sender_name_elem.text = sender_name
            
            if hasattr(message, 'chat') and message.chat:
                group_id_elem = ET.SubElement(telegram_elem, "group_id")
                group_id_elem.text = str(message.chat.id)
                
                group_name_elem = ET.SubElement(telegram_elem, "group_name")
                group_name_elem.text = message.chat.title or "Unknown"
            
            # 转发信息
            if hasattr(message, 'forward_from') and message.forward_from:
                forward_info_elem = ET.SubElement(telegram_elem, "forward_info")
                forward_from_elem = ET.SubElement(forward_info_elem, "from")
                if hasattr(message.forward_from, 'first_name'):
                    forward_name = message.forward_from.first_name
                    if hasattr(message.forward_from, 'last_name') and message.forward_from.last_name:
                        forward_name += f" {message.forward_from.last_name}"
                    forward_from_elem.text = forward_name
                
                if hasattr(message, 'forward_date'):
                    forward_date_elem = ET.SubElement(forward_info_elem, "date")
                    forward_date_elem.text = message.forward_date.strftime('%Y-%m-%d')
            
            # 格式化XML
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
            # 移除空行
            xml_lines = [line for line in xml_str.split('\n') if line.strip()]
            formatted_xml = '\n'.join(xml_lines)
            
            # 写入NFO文件
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(formatted_xml)
            
            logger.info(f"NFO文件已生成: {nfo_path}")
            return nfo_path
            
        except Exception as e:
            logger.error(f"生成NFO文件失败: {e}")
            return None
    
    def _extract_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        使用ffprobe提取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.warning(f"ffprobe执行失败: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning(f"ffprobe超时: {video_path}")
            return None
        except FileNotFoundError:
            logger.warning("ffprobe未找到，跳过视频信息提取")
            return None
        except Exception as e:
            logger.error(f"提取视频信息失败: {e}")
            return None
    
    def _extract_plot_from_message(self, message: Any) -> str:
        """
        从消息中提取剧情描述
        
        Args:
            message: 消息对象
            
        Returns:
            剧情描述文本
        """
        plot_parts = []
        
        # 添加消息文本
        if hasattr(message, 'text') and message.text:
            plot_parts.append(message.text.strip())
        
        # 添加消息说明
        if hasattr(message, 'caption') and message.caption:
            caption = message.caption.strip()
            if caption not in plot_parts:  # 避免重复
                plot_parts.append(caption)
        
        # 组合描述
        plot = '\n\n'.join(plot_parts) if plot_parts else "无描述"
        
        # 限制长度
        if len(plot) > 1000:
            plot = plot[:1000] + "..."
        
        return plot
    
    def generate_media_images(self, 
                             video_path: str, 
                             message: Any, 
                             task_data: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        生成媒体相关图片（封面、背景图、缩略图）
        
        Args:
            video_path: 视频文件路径
            message: 消息对象
            task_data: 任务数据
            
        Returns:
            包含各种图片路径的字典
        """
        if not task_data.get('download_thumbnails', True):
            return {}
        
        result = {
            'poster': None,
            'fanart': None,
            'thumb': None
        }
        
        video_dir = os.path.dirname(video_path)
        
        try:
            # 尝试从视频提取帧作为基础图片
            base_image_path = self._extract_video_frame(video_path)
            
            if base_image_path:
                # 生成封面图 (poster.jpg) - 竖版 600x900
                poster_path = os.path.join(video_dir, "poster.jpg")
                if self._create_poster_image(base_image_path, poster_path, message, task_data):
                    result['poster'] = poster_path
                
                # 生成背景图 (fanart.jpg) - 横版 1920x1080
                fanart_path = os.path.join(video_dir, "fanart.jpg")
                if self._create_fanart_image(base_image_path, fanart_path):
                    result['fanart'] = fanart_path
                
                # 生成缩略图 (thumb.jpg) - 400x300
                thumb_path = os.path.join(video_dir, "thumb.jpg")
                if self._create_thumbnail_image(base_image_path, thumb_path):
                    result['thumb'] = thumb_path
                
                # 清理临时文件
                try:
                    os.remove(base_image_path)
                except:
                    pass
            else:
                # 如果无法从视频提取帧，生成默认图片
                self._generate_default_images(video_dir, message, task_data, result)
                
        except Exception as e:
            logger.error(f"生成媒体图片失败: {e}")
            # 生成默认图片作为备用
            self._generate_default_images(video_dir, message, task_data, result)
        
        return result
    
    def _extract_video_frame(self, video_path: str, timestamp: str = "00:00:05") -> Optional[str]:
        """
        从视频中提取一帧作为基础图片
        
        Args:
            video_path: 视频文件路径
            timestamp: 提取帧的时间点
            
        Returns:
            提取的图片路径
        """
        try:
            temp_image = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            temp_image.close()
            
            # 更强大的ffmpeg命令，包含更多选项
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', timestamp,
                '-vframes', '1',
                '-q:v', '2',  # 高质量
                '-vf', 'scale=400:300:force_original_aspect_ratio=decrease,pad=400:300:(ow-iw)/2:(oh-ih)/2',  # 缩放并居中
                '-y',  # 覆盖输出文件
                temp_image.name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and os.path.exists(temp_image.name):
                # 验证生成的图片文件大小
                file_size = os.path.getsize(temp_image.name)
                if file_size > 1000:  # 至少1KB，避免空文件
                    logger.info(f"从视频提取帧成功: {temp_image.name} (大小: {file_size} bytes)")
                    return temp_image.name
                else:
                    logger.warning(f"提取的帧文件太小，可能损坏: {file_size} bytes")
                    try:
                        os.remove(temp_image.name)
                    except:
                        pass
                    return None
            else:
                logger.warning(f"ffmpeg提取帧失败 (return code: {result.returncode})")
                logger.warning(f"ffmpeg stderr: {result.stderr}")
                logger.warning(f"ffmpeg stdout: {result.stdout}")
                try:
                    os.remove(temp_image.name)
                except:
                    pass
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning(f"ffmpeg提取帧超时: {video_path}")
            try:
                os.remove(temp_image.name)
            except:
                pass
            return None
        except FileNotFoundError:
            logger.warning("ffmpeg未安装，无法提取视频帧。请安装ffmpeg: apt-get install ffmpeg")
            return None
        except Exception as e:
            logger.error(f"提取视频帧失败: {e}")
            try:
                os.remove(temp_image.name)
            except:
                pass
            return None
    
    def _create_poster_image(self, 
                           base_image_path: str, 
                           output_path: str, 
                           message: Any, 
                           task_data: Dict[str, Any]) -> bool:
        """
        创建海报图片 (竖版 600x900)
        
        Args:
            base_image_path: 基础图片路径
            output_path: 输出路径
            message: 消息对象
            task_data: 任务数据
            
        Returns:
            是否成功
        """
        try:
            with Image.open(base_image_path) as img:
                # 创建竖版画布
                poster_size = task_data.get('poster_size', (600, 900))
                poster = Image.new('RGB', poster_size, color='black')
                
                # 计算图片缩放比例，保持宽高比
                img_ratio = img.width / img.height
                poster_ratio = poster_size[0] / poster_size[1]
                
                if img_ratio > poster_ratio:
                    # 图片更宽，以高度为准
                    new_height = poster_size[1]
                    new_width = int(new_height * img_ratio)
                else:
                    # 图片更高，以宽度为准
                    new_width = poster_size[0]
                    new_height = int(new_width / img_ratio)
                
                # 缩放图片
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 居中粘贴
                x = (poster_size[0] - new_width) // 2
                y = (poster_size[1] - new_height) // 2
                poster.paste(resized_img, (x, y))
                
                # 添加标题文字（可选）
                self._add_title_to_image(poster, message, task_data)
                
                # 保存
                poster.save(output_path, 'JPEG', quality=85)
                logger.info(f"海报图片已生成: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"创建海报图片失败: {e}")
            return False
    
    def _create_fanart_image(self, base_image_path: str, output_path: str) -> bool:
        """
        创建背景图片 (横版 1920x1080)
        
        Args:
            base_image_path: 基础图片路径
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        try:
            with Image.open(base_image_path) as img:
                # 创建横版画布
                fanart_size = (1920, 1080)
                fanart = Image.new('RGB', fanart_size, color='black')
                
                # 计算缩放比例
                img_ratio = img.width / img.height
                fanart_ratio = fanart_size[0] / fanart_size[1]
                
                if img_ratio > fanart_ratio:
                    # 图片更宽，以宽度为准
                    new_width = fanart_size[0]
                    new_height = int(new_width / img_ratio)
                else:
                    # 图片更高，以高度为准
                    new_height = fanart_size[1]
                    new_width = int(new_height * img_ratio)
                
                # 缩放图片
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 居中粘贴
                x = (fanart_size[0] - new_width) // 2
                y = (fanart_size[1] - new_height) // 2
                fanart.paste(resized_img, (x, y))
                
                # 保存
                fanart.save(output_path, 'JPEG', quality=85)
                logger.info(f"背景图片已生成: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"创建背景图片失败: {e}")
            return False
    
    def _create_thumbnail_image(self, base_image_path: str, output_path: str) -> bool:
        """
        创建缩略图 (400x300)
        
        Args:
            base_image_path: 基础图片路径
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        try:
            with Image.open(base_image_path) as img:
                # 创建缩略图
                thumb_size = (400, 300)
                img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                
                # 创建画布并居中粘贴
                thumb = Image.new('RGB', thumb_size, color='black')
                x = (thumb_size[0] - img.width) // 2
                y = (thumb_size[1] - img.height) // 2
                thumb.paste(img, (x, y))
                
                # 保存
                thumb.save(output_path, 'JPEG', quality=80)
                logger.info(f"缩略图已生成: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"创建缩略图失败: {e}")
            return False
    
    def _add_title_to_image(self, 
                           image: Image.Image, 
                           message: Any, 
                           task_data: Dict[str, Any]):
        """
        在图片上添加标题文字
        
        Args:
            image: PIL图片对象
            message: 消息对象
            task_data: 任务数据
        """
        try:
            draw = ImageDraw.Draw(image)
            title = self._extract_video_title(message, "")
            
            # 限制标题长度
            if len(title) > 30:
                title = title[:30] + "..."
            
            # 尝试使用系统字体
            font_size = 24
            try:
                # 尝试加载中文字体
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/TTF/simhei.ttf",
                    "/System/Library/Fonts/PingFang.ttc",
                    "/Windows/Fonts/msyh.ttc"
                ]
                font = None
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, font_size)
                        break
                
                if not font:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # 计算文字位置（底部居中）
            bbox = draw.textbbox((0, 0), title, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (image.width - text_width) // 2
            y = image.height - text_height - 20
            
            # 绘制文字阴影
            draw.text((x + 2, y + 2), title, font=font, fill='black')
            # 绘制文字
            draw.text((x, y), title, font=font, fill='white')
            
        except Exception as e:
            logger.warning(f"添加标题文字失败: {e}")
    
    def _generate_default_images(self, 
                                video_dir: str, 
                                message: Any, 
                                task_data: Dict[str, Any], 
                                result: Dict[str, Optional[str]]):
        """
        生成默认图片（当无法从视频提取帧时）
        
        Args:
            video_dir: 视频目录
            message: 消息对象
            task_data: 任务数据
            result: 结果字典
        """
        try:
            title = self._extract_video_title(message, "")
            
            # 生成默认海报
            poster_path = os.path.join(video_dir, "poster.jpg")
            if self._create_default_poster(poster_path, title, task_data):
                result['poster'] = poster_path
            
            # 生成默认背景图
            fanart_path = os.path.join(video_dir, "fanart.jpg")
            if self._create_default_fanart(fanart_path, title):
                result['fanart'] = fanart_path
            
            # 生成默认缩略图
            thumb_path = os.path.join(video_dir, "thumb.jpg")
            if self._create_default_thumbnail(thumb_path, title):
                result['thumb'] = thumb_path
                
        except Exception as e:
            logger.error(f"生成默认图片失败: {e}")
    
    def _create_default_poster(self, output_path: str, title: str, task_data: Dict[str, Any]) -> bool:
        """创建默认海报图片"""
        try:
            poster_size = task_data.get('poster_size', (600, 900))
            
            # 创建带渐变的背景
            poster = Image.new('RGB', poster_size, color='#2c3e50')
            draw = ImageDraw.Draw(poster)
            
            # 创建蓝色渐变背景
            for i in range(poster_size[1]):
                # 从深蓝到较浅的蓝色
                ratio = i / poster_size[1]
                r = int(44 + (52 - 44) * ratio)    # 44 -> 52
                g = int(62 + (152 - 62) * ratio)   # 62 -> 152  
                b = int(80 + (219 - 80) * ratio)   # 80 -> 219
                color = f'#{r:02x}{g:02x}{b:02x}'
                draw.line([(0, i), (poster_size[0], i)], fill=color)
            
            # 添加装饰性的圆形
            circle_color = '#ffffff'
            alpha_overlay = Image.new('RGBA', poster_size, (255, 255, 255, 0))
            alpha_draw = ImageDraw.Draw(alpha_overlay)
            
            # 绘制半透明圆形
            alpha_draw.ellipse([50, 100, 150, 200], fill=(255, 255, 255, 30))
            alpha_draw.ellipse([poster_size[0] - 150, poster_size[1] - 200, poster_size[0] - 50, poster_size[1] - 100], fill=(255, 255, 255, 30))
            
            poster = Image.alpha_composite(poster.convert('RGBA'), alpha_overlay).convert('RGB')
            draw = ImageDraw.Draw(poster)
            
            # 添加视频图标
            self._draw_video_icon(draw, poster_size[0] // 2, poster_size[1] // 3, 60, '#ffffff')
            
            # 添加标题
            if len(title) > 20:
                title = title[:20] + "..."
            
            # 加载字体
            font = self._get_font(32)
            
            # 居中绘制标题
            bbox = draw.textbbox((0, 0), title, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (poster_size[0] - text_width) // 2
            y = poster_size[1] // 2 + 50
            
            # 绘制文字阴影
            draw.text((x + 2, y + 2), title, font=font, fill='#000000')
            # 绘制主文字
            draw.text((x, y), title, font=font, fill='#ffffff')
            
            poster.save(output_path, 'JPEG', quality=85)
            logger.info(f"默认海报图片已生成: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建默认海报失败: {e}")
            return False
    
    def _create_default_fanart(self, output_path: str, title: str) -> bool:
        """创建默认背景图片"""
        try:
            fanart = Image.new('RGB', (1920, 1080), color='#34495e')
            draw = ImageDraw.Draw(fanart)
            
            # 创建横向渐变
            for i in range(1920):
                ratio = i / 1920
                r = int(52 + (46 - 52) * ratio)    # 52 -> 46
                g = int(73 + (204 - 73) * ratio)   # 73 -> 204
                b = int(94 + (113 - 94) * ratio)   # 94 -> 113
                color = f'#{r:02x}{g:02x}{b:02x}'
                draw.line([(i, 0), (i, 1080)], fill=color)
            
            # 添加装饰元素
            self._draw_video_icon(draw, 1920 // 2, 1080 // 2, 120, '#ffffff')
            
            fanart.save(output_path, 'JPEG', quality=85)
            logger.info(f"默认背景图片已生成: {output_path}")
            return True
        except Exception as e:
            logger.error(f"创建默认背景图失败: {e}")
            return False
    
    def _create_default_thumbnail(self, output_path: str, title: str) -> bool:
        """创建默认缩略图"""
        try:
            thumb = Image.new('RGB', (400, 300), color='#3498db')
            draw = ImageDraw.Draw(thumb)
            
            # 创建对角渐变
            for i in range(300):
                ratio = i / 300
                r = int(52 + (231 - 52) * ratio)    # 52 -> 231
                g = int(152 + (76 - 152) * ratio)   # 152 -> 76
                b = int(219 + (60 - 219) * ratio)   # 219 -> 60
                color = f'#{r:02x}{g:02x}{b:02x}'
                draw.line([(0, i), (400, i)], fill=color)
            
            # 添加播放图标
            self._draw_play_icon(draw, 200, 150, 40, '#ffffff')
            
            # 添加标题（如果不为空）
            if title and title != "Media":
                font = self._get_font(16)
                if len(title) > 25:
                    title = title[:25] + "..."
                
                bbox = draw.textbbox((0, 0), title, font=font)
                text_width = bbox[2] - bbox[0]
                
                x = (400 - text_width) // 2
                y = 250
                
                # 绘制文字阴影
                draw.text((x + 1, y + 1), title, font=font, fill='#000000')
                # 绘制主文字
                draw.text((x, y), title, font=font, fill='#ffffff')
            
            thumb.save(output_path, 'JPEG', quality=80)
            logger.info(f"默认缩略图已生成: {output_path}")
            return True
        except Exception as e:
            logger.error(f"创建默认缩略图失败: {e}")
            return False
    
    def _get_font(self, size: int):
        """获取字体，优先尝试系统字体"""
        try:
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/TTF/simhei.ttf",
                "/System/Library/Fonts/PingFang.ttc",
                "/Windows/Fonts/msyh.ttc"
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()
    
    def _draw_video_icon(self, draw, x: int, y: int, size: int, color: str):
        """绘制视频图标"""
        try:
            # 绘制视频播放按钮（三角形）
            half_size = size // 2
            triangle_points = [
                (x - half_size, y - half_size),
                (x - half_size, y + half_size),
                (x + half_size, y)
            ]
            draw.polygon(triangle_points, fill=color)
            
            # 绘制外框
            draw.ellipse([x - half_size - 10, y - half_size - 10, 
                         x + half_size + 10, y + half_size + 10], 
                        outline=color, width=3)
        except Exception as e:
            logger.warning(f"绘制视频图标失败: {e}")
    
    def _draw_play_icon(self, draw, x: int, y: int, size: int, color: str):
        """绘制播放图标"""
        try:
            # 绘制播放按钮（三角形）
            half_size = size // 2
            triangle_points = [
                (x - half_size // 2, y - half_size),
                (x - half_size // 2, y + half_size),
                (x + half_size, y)
            ]
            draw.polygon(triangle_points, fill=color)
        except Exception as e:
            logger.warning(f"绘制播放图标失败: {e}")