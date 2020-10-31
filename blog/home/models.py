from django.db import models
from django.utils import timezone
from users.models import User


class ArticleCategory(models.Model):
    """文章分类"""
    # 栏目标题
    title = models.CharField(max_length=100, blank=True)
    # 创建时间
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "tb_category"
        verbose_name = "类别管理"
        verbose_name_plural = verbose_name


class Article(models.Model):
    """文章"""
    # 定义文章作者author,author通过models.ForeignKey外键与内建的User模型关联在一起
    # 参数on_delete用于指定数据删除的方式，避免两个关联表的数据不一致
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    # 文章标题图
    avatar = models.ImageField(upload_to="article/%Y%m%d", blank=True)
    # 文章栏目的“一对多”外键
    category = models.ForeignKey(ArticleCategory, null=True, blank=True, on_delete=models.CASCADE, related_name="article")
    # 文章标签
    tags = models.CharField(max_length=20, blank=True)
    # 文章标题
    title = models.CharField(max_length=100, null=False, blank=False)
    # 概要
    sumary = models.CharField(max_length=200, null=False, blank=False)
    # 文章正文
    content = models.TextField()
    # 浏览量
    total_views = models.PositiveIntegerField(default=0)
    # 文章评论数 PositiveIntegerField-正整数
    comments_count = models.PositiveIntegerField(default=0)
    # 文章创建时间 参数default=timezone.now 指定其在创建数据时将默认写入当前时间
    created = models.DateTimeField(default=timezone.now)
    # 文章更新时间 参数auto_now=True 指定每次数据更新时自动写入当前时间
    updated = models.DateTimeField(auto_now=True)

    # 内部类class Meta 用于给model定义元数据
    class Meta:
        # ordering 指定模型返回的数据的排列顺序 -created 表明数据应该以创建时间倒序排列
        ordering = ("-created",)
        db_table = "tb_article"
        verbose_name = "文章管理"
        verbose_name_plural = verbose_name

    # 函数__str__定义当调用对象的str()方法时的返回值内容，最常见的就是在Django管理后台中作为对象的显示值
    def __str__(self):
        # 将文章标题返回
        return self.title


class Comment(models.Model):
    # 评论内容
    content = models.TextField()
    # 评论的文章
    # SET_NULL: 置空模式，删除的时候，外键字段被设置为空，前提就是blank=True, null=True,定义该字段的时候，允许为空。
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True)
    # 发表评论的用户
    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True)
    # 评论发布时间
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.article.title

    class Meta:
        db_table = "tb_comment"
        verbose_name = "评论管理"
        verbose_name_plural = verbose_name





































