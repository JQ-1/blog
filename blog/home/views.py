from django.shortcuts import render
from django.views import View
from home.models import ArticleCategory, Article
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
        #  detail/?id=xxx&page_num=xxx&page_size=xxx
        # 1.接收文章的id信息
        id = request.GET.get("id")
        # 2.根据文章id 进行文章数据的查询
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return render(request, '404.html')
        # 3.查询分类数据
        categories = ArticleCategory.objects.all()
        # 4.组织模板数据
        context = {
            'categories': categories,
            'category': article.category,
            'article': article,
        }
        return render(request, "detail.html", context=context)
