"""
初始化models包，确保按正确顺序导入所有模型，解决循环依赖问题
"""

# 首先导入不依赖其他模型的基本模型
from .user import User
from .user_settings import UserSettings

# 然后导入依赖上述模型的其他模型
# 示例: from .other_model import OtherModel