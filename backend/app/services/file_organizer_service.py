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
        # 优先使用消息文本作为标题
        if hasattr(message, 'text') and message.text:
            title = message.text.strip()
            # 如果文本太长，截取前50个字符
            if len(title) > 50:
                title = title[:50] + "..."
            return title
        
        # 其次使用消息说明
        if hasattr(message, 'caption') and message.caption:
            caption = message.caption.strip()
            if len(caption) > 50:
                caption = caption[:50] + "..."
            return caption
        
        # 最后使用文件名（去除扩展名）
        if original_filename:
            title = os.path.splitext(original_filename)[0]
            return title
        
        # 默认标题
        return "Media"
    
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