"""
模型初始化 - 确保SQLAlchemy能够正确解析模型关系
"""
# 先导入User
from .user import User
# 再导入依赖于User的模型
from .user_settings import UserSettings
# 其他模型
from .rule import *
from .task_rule_association import TaskRuleAssociation
from .log import *
from .telegram import *
from .config import *