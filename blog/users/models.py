from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    # 手机号码  unique：为唯一性字段
    mobile = models.CharField(max_length=11, unique=True, blank=False)
    # 头像  upload_to:为保存到响应的子目录中
    avatar = models.ImageField(upload_to='avatar/%Y%m%d', blank=True)
    # 个人简介
    user_desc = models.TextField(max_length=500, blank=True)

    # 修改认证的字段
    USERNAME_FIELD = "mobile"

    # 创建超级管理员的需要必须输入的字段
    REQUIRED_FIELDS = ["username", "email"]

    class Meta:
        db_table = "tb_users"  # 修改默认的表名
        verbose_name = "用户管理"  # admin后台展示
        verbose_name_plural = verbose_name  # admin后台展示

    def __str__(self):
        return self.mobile
