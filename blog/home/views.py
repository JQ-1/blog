from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from home.models import ArticleCategory, Article, Comment
from django.http import HttpResponseNotFound
from django.core.paginator import Paginator, EmptyPage


class IndexView(View):
    """首页"""
    def get(self, request):
        """提供首页界面
        1.获取所有的分类信息
        2.接收用户点击的id
        3.根据分类id进行分类的查询
        4.获取分页参数
        5.根据分类信息查询文章数据
        6.创建分页器
        7.进行分页处理
        8.组织数据传递给模板
        """
        # 1.获取所有的分类信息
        categories = ArticleCategory.objects.all()
        # 2.接收用户点击的分类id  ?cat_id=xxx&page_num=xxx&page_size=xxx
        cat_id = request.GET.get("cat_id", 1)
        page_num = request.GET.get("page_num", 1)
        page_size = request.GET.get("page_size", 10)
        # 3.根据分类id进行分类的查询
        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseNotFound("没有此分类")
        # 4.根据分类信息查询文章数据
        articles = Article.objects.filter(category=category)
        # 5.创建分页器 参数1：所有文章 参数2：每页n条数据
        paginator = Paginator(articles, page_size)
        # 6.进行分页处理
        try:
            # 获取指定页的数据
            page_articles = paginator.page(page_num)
        except EmptyPage:
            # 如果没有分页数据，默认给用户404
            return HttpResponseNotFound("empty page")
        # 7.获取列表页总页数
        total_page = paginator.num_pages
        # 8.组织数据传递给模板
        context = {
            "categories": categories,
            "category": category,
            "articles": page_articles,
            "page_size": page_size,
            "total_page": total_page,
            "page_num": page_num,
        }
        return render(request, "index.html", context=context)


class DetailView(View):
    """"详情页面展示"""
    def get(self, request):
        """
        1.接收文章的id信息
        2.根据文章id进行文章数据的查询
        3.查询分类数据
        4.获取评论分页请求参数
        5.根据文章信息查询评论数据
        6.创建分页器
        7.进行分页处理
        8.组织模板数据
        :param request:
        :return:
        """
        #  detail/?id=xxx&page_num=xxx&page_size=xxx
        # 1.接收文章的id信息
        id = request.GET.get("id")
        # 2.根据文章id 进行文章数据的查询
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return render(request, '404.html')
        else:
            # 浏览量：每次请求文章详情时给浏览量＋1
            article.total_views += 1
            article.save()
        # 3.查询分类数据
        categories = ArticleCategory.objects.all()

        # 获取热点文章：查询浏览量前10的文章数据
        hot_articles = Article.objects.order_by("-total_views")[:9]

        # 4.获取评论分页请求参数
        page_num = request.GET.get("page_num", 1)
        page_size = request.GET.get("page_size", 5)
        # 5.根据文章信息查询评论数据
        comments = Comment.objects.filter(article=article).order_by("-created")
        # 获取评论总数
        total_count = comments.count()
        # 6.创建分页器:每页N条记录
        paginator = Paginator(comments, page_size)
        # 7.进行分页处理
        try:
            page_comments = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，默认给用户404
            return HttpResponseNotFound("empty page")
        # 获取评论页总页数
        total_page = paginator.num_pages

        # 4.组织模板数据
        context = {
            'categories': categories,
            'category': article.category,
            'article': article,
            "hot_articles": hot_articles,
            "total_count": total_count,
            "comments": page_comments,
            "page_size": page_size,
            "total_page": total_page,
            "page_num": page_num
        }
        return render(request, "detail.html", context=context)

    def post(self, request):
        # 1.先接收用户信息
        user = request.user
        # 2.判断用户是否登陆
        if user and user.is_authenticated:
            # 3.登陆用户则可以接收form数据
            # 3.1接收评论数据
            id = request.POST.get("id")
            content = request.POST.get("content")
            # 3.2验证文章是否存在
            try:
                article = Article.objects.get(id=id)
            except Article.DoesNotExist:
                return HttpResponseNotFound("没有此文章")
            # 3.3保存评论数据
            Comment.objects.create(
                content=content,
                article=article,
                user=user
            )
            # 3.4修改文章的评论数量
            article.comments_count += 1
            article.save()
            # 刷新当前页面（页面重定向）拼接跳转路由
            path = reverse("home:detail") + "?id={}".format(article.id)
            return redirect(path)
        # 4.未登录用户则跳转到登陆页面
        else:
            return redirect(reverse("users:login"))










