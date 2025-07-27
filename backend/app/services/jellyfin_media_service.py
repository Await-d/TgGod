"""
Jellyfin 兼容的媒体下载服务
支持生成 NFO 文件、组织文件结构、处理封面图等
"""

import os
import logging
import shutil
import asyncio
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
from ..models.telegram import TelegramMessage, TelegramGroup
from ..models.rule import DownloadTask, FilterRule
from ..utils.jellyfin_nfo_generator import JellyfinNFOGenerator, JellyfinPathManager
from .media_downloader import TelegramMediaDownloader

logger = logging.getLogger(__name__)

class JellyfinMediaService:
    """Jellyfin 兼容的媒体下载服务"""
    
    def __init__(self):
        self.nfo_generator = JellyfinNFOGenerator()
        self.path_manager = JellyfinPathManager()
        self.media_downloader = TelegramMediaDownloader()
        
    async def download_media_with_jellyfin_structure(self,
                                                   message: TelegramMessage,
                                                   group: TelegramGroup,
                                                   task: DownloadTask,
                                                   jellyfin_config: Dict[str, Any]) -> Tuple[bool, str, Dict[str, str]]:
        """
        使用 Jellyfin 兼容结构下载媒体
        
        Args:
            message: Telegram 消息
            group: Telegram 群组
            task: 下载任务
            jellyfin_config: Jellyfin 配置选项
            
        Returns:
            (成功状态, 错误信息, 文件路径字典)
        """
        try:
            # 生成 Jellyfin 路径结构
            path_info = self.path_manager.generate_media_path(
                base_path=task.download_path,
                group=group,
                message=message,
                task=task,
                rule=task.rule,  # 传递规则对象以获取关键词
                use_series_structure=jellyfin_config.get('use_series_structure', False)
            )
            
            if not path_info:
                return False, "生成路径结构失败", {}
            
            # 确保目录存在
            os.makedirs(path_info['episode_dir'], exist_ok=True)
            
            # 下载主媒体文件
            success, main_file_path = await self._download_main_media(message, path_info, jellyfin_config)
            if not success:
                return False, f"下载主媒体文件失败: {main_file_path}", {}
            
            result_paths = {'main_media': main_file_path}
            
            # 生成 NFO 文件
            if jellyfin_config.get('include_metadata', True):
                nfo_success = await self._generate_nfo_file(message, group, task, path_info, jellyfin_config)
                if nfo_success:
                    result_paths['nfo'] = os.path.join(path_info['episode_dir'], f"{path_info['video_filename']}.nfo")
            
            # 处理封面图和缩略图
            if jellyfin_config.get('download_thumbnails', True):
                await self._process_images(message, path_info, jellyfin_config, result_paths)
            
            logger.info(f"Jellyfin 媒体下载完成: {main_file_path}")
            return True, "", result_paths
            
        except Exception as e:
            logger.error(f"Jellyfin 媒体下载失败: {e}")
            return False, str(e), {}
    
    async def _download_main_media(self, 
                                 message: TelegramMessage, 
                                 path_info: Dict[str, str],
                                 jellyfin_config: Dict[str, Any]) -> Tuple[bool, str]:
        """下载主媒体文件"""
        try:
            # 确定文件扩展名
            file_extension = self._get_file_extension(message)
            
            # 生成文件路径
            filename = f"{path_info['video_filename']}{file_extension}"
            file_path = os.path.join(path_info['episode_dir'], filename)
            
            # 检查文件是否已存在
            if os.path.exists(file_path) and not jellyfin_config.get('force_redownload', False):
                logger.info(f"文件已存在，跳过下载: {file_path}")
                return True, file_path
            
            # 执行下载
            success = await self.media_downloader.download_file(
                file_id=message.media_file_id,
                file_path=file_path,
                chat_id=message.group.telegram_id,
                message_id=message.message_id
            )
            
            if success and os.path.exists(file_path):
                logger.info(f"主媒体文件下载成功: {file_path}")
                return True, file_path
            else:
                logger.error(f"主媒体文件下载失败: {file_path}")
                return False, "下载失败"
                
        except Exception as e:
            logger.error(f"下载主媒体文件异常: {e}")
            return False, str(e)
    
    async def _generate_nfo_file(self,
                               message: TelegramMessage,
                               group: TelegramGroup,
                               task: DownloadTask,
                               path_info: Dict[str, str],
                               jellyfin_config: Dict[str, Any]) -> bool:
        """生成 NFO 文件"""
        try:
            nfo_path = os.path.join(path_info['episode_dir'], f"{path_info['video_filename']}.nfo")
            
            if jellyfin_config.get('use_series_structure', False):
                # 生成剧集 NFO
                success = self.nfo_generator.generate_episode_nfo(
                    message=message,
                    group=group,
                    task=task,
                    episode_title=path_info['video_title'],
                    season=1,  # 默认第一季
                    episode=message.message_id % 10000,  # 使用消息ID作为集数
                    output_path=nfo_path
                )
            else:
                # 生成电影 NFO
                success = self.nfo_generator.generate_movie_nfo(
                    message=message,
                    group=group,
                    task=task,
                    video_title=path_info['video_title'],
                    video_file_path=path_info['episode_dir'],
                    output_path=nfo_path
                )
            
            if success:
                logger.info(f"NFO 文件生成成功: {nfo_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"生成 NFO 文件失败: {e}")
            return False
    
    async def _process_images(self,
                            message: TelegramMessage,
                            path_info: Dict[str, str],
                            jellyfin_config: Dict[str, Any],
                            result_paths: Dict[str, str]):
        """处理封面图和缩略图"""
        try:
            episode_dir = path_info['episode_dir']
            
            # 处理现有缩略图
            if message.media_thumbnail_path and os.path.exists(message.media_thumbnail_path):
                await self._process_existing_thumbnail(message.media_thumbnail_path, episode_dir, jellyfin_config)
            else:
                # 生成默认图片
                await self._generate_default_images(message, path_info, episode_dir, jellyfin_config)
            
            # 记录生成的图片路径
            poster_path = os.path.join(episode_dir, "poster.jpg")
            fanart_path = os.path.join(episode_dir, "fanart.jpg")
            thumb_path = os.path.join(episode_dir, "thumb.jpg")
            
            if os.path.exists(poster_path):
                result_paths['poster'] = poster_path
            if os.path.exists(fanart_path):
                result_paths['fanart'] = fanart_path
            if os.path.exists(thumb_path):
                result_paths['thumb'] = thumb_path
                
        except Exception as e:
            logger.error(f"处理图片失败: {e}")
    
    async def _process_existing_thumbnail(self, 
                                        thumbnail_path: str, 
                                        episode_dir: str,
                                        jellyfin_config: Dict[str, Any]):
        """处理现有的缩略图"""
        try:
            with Image.open(thumbnail_path) as img:
                # 生成海报 (竖版)
                poster_size = jellyfin_config.get('poster_size', (600, 900))
                poster = self._resize_image_for_poster(img, poster_size)
                poster_path = os.path.join(episode_dir, "poster.jpg")
                poster.save(poster_path, "JPEG", quality=85)
                
                # 生成背景图 (横版)
                fanart_size = jellyfin_config.get('fanart_size', (1920, 1080))
                fanart = self._resize_image_for_fanart(img, fanart_size)
                fanart_path = os.path.join(episode_dir, "fanart.jpg")
                fanart.save(fanart_path, "JPEG", quality=85)
                
                # 生成缩略图
                thumb_size = jellyfin_config.get('thumbnail_size', (400, 300))
                thumb = img.copy()
                thumb.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                thumb_path = os.path.join(episode_dir, "thumb.jpg")
                thumb.save(thumb_path, "JPEG", quality=80)
                
                logger.info(f"图片处理完成: {episode_dir}")
                
        except Exception as e:
            logger.error(f"处理现有缩略图失败: {e}")
    
    async def _generate_default_images(self,
                                     message: TelegramMessage,
                                     path_info: Dict[str, str],
                                     episode_dir: str,
                                     jellyfin_config: Dict[str, Any]):
        """生成默认图片"""
        try:
            # 创建默认海报
            poster_size = jellyfin_config.get('poster_size', (600, 900))
            poster = self._create_text_image(
                size=poster_size,
                text=path_info['video_title'],
                bg_color=(30, 30, 30),
                text_color=(255, 255, 255)
            )
            poster_path = os.path.join(episode_dir, "poster.jpg")
            poster.save(poster_path, "JPEG", quality=85)
            
            # 创建默认背景图
            fanart_size = jellyfin_config.get('fanart_size', (1920, 1080))
            fanart = self._create_text_image(
                size=fanart_size,
                text=f"{path_info['group_name']}\n{path_info['video_title']}",
                bg_color=(20, 20, 20),
                text_color=(200, 200, 200)
            )
            fanart_path = os.path.join(episode_dir, "fanart.jpg")
            fanart.save(fanart_path, "JPEG", quality=85)
            
            # 创建默认缩略图
            thumb_size = jellyfin_config.get('thumbnail_size', (400, 300))
            thumb = self._create_text_image(
                size=thumb_size,
                text=path_info['video_title'],
                bg_color=(50, 50, 50),
                text_color=(255, 255, 255)
            )
            thumb_path = os.path.join(episode_dir, "thumb.jpg")
            thumb.save(thumb_path, "JPEG", quality=80)
            
            logger.info(f"默认图片生成完成: {episode_dir}")
            
        except Exception as e:
            logger.error(f"生成默认图片失败: {e}")
    
    def _resize_image_for_poster(self, img: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """调整图片大小用作海报 (竖版)"""
        # 如果图片是横版，旋转90度或进行裁剪
        if img.width > img.height:
            # 横版图片，裁剪为正方形然后调整
            size = min(img.width, img.height)
            left = (img.width - size) // 2
            top = (img.height - size) // 2
            img = img.crop((left, top, left + size, top + size))
        
        # 调整为目标尺寸
        img = img.resize(target_size, Image.Resampling.LANCZOS)
        return img
    
    def _resize_image_for_fanart(self, img: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """调整图片大小用作背景图 (横版)"""
        # 保持横版比例，居中裁剪
        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]
        
        if img_ratio > target_ratio:
            # 图片更宽，按高度缩放
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # 居中裁剪
            left = (new_width - target_size[0]) // 2
            img = img.crop((left, 0, left + target_size[0], target_size[1]))
        else:
            # 图片更高，按宽度缩放
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # 居中裁剪
            top = (new_height - target_size[1]) // 2
            img = img.crop((0, top, target_size[0], top + target_size[1]))
        
        return img
    
    def _create_text_image(self, 
                          size: Tuple[int, int], 
                          text: str, 
                          bg_color: Tuple[int, int, int],
                          text_color: Tuple[int, int, int]) -> Image.Image:
        """创建带文字的图片"""
        img = Image.new('RGB', size, bg_color)
        draw = ImageDraw.Draw(img)
        
        # 尝试使用系统字体
        try:
            # 根据图片大小选择字体大小
            font_size = min(size[0], size[1]) // 20
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        if font:
            # 计算文字位置 (居中)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
            
            draw.text((x, y), text, fill=text_color, font=font)
        
        return img
    
    def _get_file_extension(self, message: TelegramMessage) -> str:
        """获取文件扩展名"""
        if message.media_filename:
            _, ext = os.path.splitext(message.media_filename)
            if ext:
                return ext
        
        # 根据媒体类型返回默认扩展名
        media_type = message.media_type
        if media_type == "video":
            return ".mp4"
        elif media_type == "photo":
            return ".jpg"
        elif media_type == "audio":
            return ".mp3"
        elif media_type == "voice":
            return ".ogg"
        elif media_type == "document":
            return ".bin"
        else:
            return ".bin"