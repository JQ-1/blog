from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from utils.response_code import RETCODE
import logging
logger = logging.getLogger("django")
from random import randint
from libs.yuntongxun.sms import CCP
import re
from users.models import User
from django.db import DatabaseError
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from home.models import ArticleCategory, Article


class RegisterView(View):
    """用户注册"""
    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, "register.html")

    def post(self, request):
        # 1.接收--表单
        mobile = request.POST.get("mobile")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        smscode = request.POST.get("sms_code")
        # 2.校验
        # 2.1参数是否齐全
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest("缺少必传参数")
        # 2.2手机号的格式是否正确
        if not re.match(r"^1[3-9]\d{9}$", mobile):
            return HttpResponseBadRequest("请输入正确的手机号")
        # 2.3密码的格式是否正确：8-20为字母或数字
        if not re.match(r"^[0-9A-Za-z]{8,20}$", password):
            return HttpResponseBadRequest("请输入8-20位数字或字母的密码")
        # 2.4密码和确认密码是否一致
        if password != password2:
            return HttpResponseBadRequest("两次输入的密码不一致")
        # 2.5短信验证码是否会让redis中的一致
        redis_conn = get_redis_connection("default")
        redis_sms_code = redis_conn.get("sms:%s" % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest("短信验证码已经过期")
        if smscode != redis_sms_code.decode():
            return HttpResponseBadRequest("短信验证码错误")
        # 3.处理：保存注册信息
        try:
            # 使用create_user可以对密码进行加密
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
        except DatabaseError as e:
            logging.error(e)
            return HttpResponseBadRequest("注册失败")
        # 实现状态保持
        login(request, user)

        # 4.返回：重定向到首页
        # redirect是进行重定向
        # reverse是可以通过namespace:name来获取到视图所对应的路由
        response = redirect(reverse("home:index"))
        # 设置cookie
        # 登录状态，会话结束后自动过期
        response.set_cookie("is_login", True)
        # 设置用户名有效期一个月
        response.set_cookie("username", user.username)
        return response


class ImageCodeView(View):
    def get(self, request):
        # 1.接收数据：获取前端传递过来的参数
        uuid = request.GET.get("uuid")
        # 2.校验数据：判断参数是否为None
        if uuid is None:
            return HttpResponseBadRequest("请求参数错误")
        # 3.处理数据：
        # 3.1 获取验证码内容和验证码图片二进制数据
        text, image = captcha.generate_captcha()
        # 3.2 将图片内容保存到redis中，并设置过期时间
        redis_conn = get_redis_connection("default")
        # setex(键key,过期时间seconds,值value)
        redis_conn.setex("img:%s" % uuid, 300, text)
        # 4.返回响应：将生成的图片以content_type为image/jpeg的形式返回请求
        return HttpResponse(image, content_type="image/jpeg")


class SmsCodeView(View):
    def get(self, request):
        # 1.接收--查询字符串
        mobile = request.GET.get('mobile')
        image_code = request.GET.get("image_code")
        uuid = request.GET.get("uuid")
        # 2.校验
        # 2.1验证参数是否齐全
        if not all([mobile, image_code, uuid]):
            return JsonResponse({"code":RETCODE.NECESSARYPARAMERR, "errmsg":"缺少必传参数"})
        # 2.2图片验证码的验证
        # 连接redis,获取redis中的图片验证码
        redis_conn = get_redis_connection("default")
        redis_image_code = redis_conn.get("img:%s" % uuid)
        # 判断图片验证码是否存在
        if redis_image_code is None:
            return JsonResponse({"code":RETCODE.IMAGECODEERR, 'errmsg':"图片验证码失效"})
        # 如果图片验证码未过期，获取验证码之后将其删除，避免恶意测试图形验证码
        try:
            redis_conn.delete("img:%s" % uuid)
        except Exception as e:
            logger.error(e)
        # 比对图片验证码,注意大小写和redis存储类型为bytes
        redis_image_code = redis_image_code.decode()
        if redis_image_code.lower() != image_code.lower():
            return JsonResponse({"code":RETCODE.IMAGECODEERR, "errmsg": "输入图像验证码有误"})
        # 3.处理
        # 3.1生成短信验证码：6位数
        sms_code = "%06d" % randint(0, 999999)
        # 将验证码输出在控制台，方便调试
        logger.info(sms_code)
        # 3.2保存短信验证码到redis中,并设置有效期
        redis_conn.setex("sms:%s" % mobile, 300, sms_code)
        # 3.3发送短信
        CCP().send_template_sms(mobile, [sms_code,5],1)
        # 4.返回
        return JsonResponse({"code": RETCODE.OK, 'ERRMSG':"发送短信成功"})


class LoginView(View):
    """登陆"""
    def get(self, request):
        """登陆页面展示"""
        return render(request, "login.html")

    def post(self, request):
        # 1.接收
        mobile = request.POST.get("mobile")
        password = request.POST.get("password")
        remember = request.POST.get("remember")

        # 2.校验
        # 2.1校验参数是否齐全
        if not all([mobile, password]):
            return HttpResponseBadRequest("缺少必传参数")
        # 2.2判断手机号是否正确
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest("请输入正确的手机号")
        # 2.3判断密码是否是8-20位字母或数字
        if not re.match(r'^[0-9a-zA-Z]{8,20}$', password):
            return HttpResponseBadRequest("密码最少8位，最长20位")
        # 2.4认证登陆用户
        # 采用系统自带的认证方法进行认证，如果认证通过，会返回user,认证失败会返回None
        # 默认的认证方法是针对username字段进行用户名的判断，当前的判断信息是手机号，需要修改认证字段
        # 认证字段已在User模型中的USERNAME_FILED = 'mobile'修改
        user = authenticate(mobile=mobile, password=password)
        if user is None:
            return HttpResponseBadRequest("用户名或密码错误")

        # 3处理
        # 实现状态保持
        login(request, user)

        # 响应登陆结果
        # 根据next参数来进行页面的跳转 http://127.0.0.1:8000/accounts/login/?next=/center/
        next = request.GET.get("next")
        if next:
            response = redirect(next)
        else:
            response = redirect(reverse("home:index"))
        # 设置状态保持周期
        if remember != "on":
            # 没有记住用户信息：浏览器会话结束就过期
            request.session.set_expiry(0)
            # 设置cookie
            response.set_cookie("is_login", True)
            response.set_cookie("username", user.username, max_age=14*24*3600)
        else:
            # 记住用户信息：None表示两周后过期
            request.session.set_expiry(None)
            # 设置cookie
            response.set_cookie("is_login", True, max_age=14*24*3600)
            response.set_cookie("username", user.username, max_age=14*24*3600)

        # 4返回响应
        return response


class LogoutView(View):
    def get(self, request):
        # 清理session
        logout(request)
        # 退出登录，重定向到登录页
        response = redirect(reverse("home:index"))
        # 退出时清除cookie中的登陆状态
        response.delete_cookie("is_login")
        return response


class ForgetPasswordView(View):
    """忘记密码"""
    def get(self, request):
        return render(request, "forget_password.html")

    def post(self, request):
        # 1.接收
        mobile = request.POST.get("mobile")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        sms_code = request.POST.get("sms_code")
        # 2.校验
        # 2.1验证参数是否齐全
        if not all([mobile, password, password2, sms_code]):
            return HttpResponseBadRequest("缺少必传参数")
        # 2.2判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest("请输入正确的手机号")
        # 2.3判断密码是否符合要求
        if not re.match(r'^[0-9a-zA-Z]{8,20}$', password):
            return HttpResponseBadRequest("请输入8-20位的数字或字母")
        # 2.4 判断两次密码输入是否一致
        if password != password2:
            return HttpResponseBadRequest("两次输入的密码不一致")
        # 2.5验证短信验证码
        redis_conn = get_redis_connection("default")
        redis_sms_code = redis_conn.get("sms:%s" % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest("短信验证码已过期")
        if sms_code != redis_sms_code.decode():
            return HttpResponseBadRequest("短信验证码错误")

        # 3.处理：
        try:
            # 3.1根据手机号进行用户信息查询
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            try:
                # 3.2如果手机号没有查询出用户信息，则进行新用户的创建
                User.objects.create_user(username=mobile, mobile=mobile, password=password)
            except Exception:
                return HttpResponseBadRequest("修改失败，请稍后再试")
        else:
            # 3.1如果手机号查出用户信息则进行用户密码的修改
            user.set_password(password)
            user.save()

        # 3.3进行页面跳转，跳转到登陆页面
        response = redirect(reverse("users:login"))
        # 4.返回响应
        return response


# LoginRequiredMixin 如果用户未登录的话，则会进行默认的跳转
# 默认的跳转链接是：http://127.0.0.1:8000/accounts/login/?next=/xxxx/
class UserCenterView(LoginRequiredMixin, View):
    """用户中心"""
    def get(self, request):
        """页面展示"""
        # 获取用户信息
        user = request.user
        # 组织模板进行渲染数据
        context = {
            "username": user.username,
            "mobile":user.mobile,
            "avatar" :user.avatar.url if user.avatar else None,
            "user_desc": user.user_desc
        }
        return render(request, "center.html", context=context)

    def post(self, request):
        # 1.接收数据
        user = request.user
        # 如果用户没有填写，则使用原用户名
        username = request.POST.get("username", user.username)
        user_desc = request.POST.get("desc", user.user_desc)
        avatar = request.FILES.get("avatar")
        # 2.修改数据库数据
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest("更新失败，请稍后再试")
        # 3.返回响应，刷新页面
        response = redirect(reverse("users:center"))
        # 更新cookie信息
        # username = json.dumps(username)
        response.set_cookie("username", username, max_age=30*24*3600)
        return response


class WriteBlogView(LoginRequiredMixin, View):
    """写博客"""
    def get(self, request):
        """写博客页面展示"""
        # 获取博客分类信息
        categories = ArticleCategory.objects.all()
        context = {
            "categories": categories
        }
        return render(request, "write_blog.html", context=context)

    def post(self, request):
        # 1.接收数据
        avatar = request.FILES.get("avatar")
        title = request.POST.get("title")
        category_id = request.POST.get("category")
        tags = request.POST.get("tags")
        sumary = request.POST.get("sumary")
        content = request.POST.get("content")
        user = request.user
        # 2.验证数据
        # 2.1 验证数据是否齐全
        if not all([avatar, title, category_id,sumary, content]):
            return HttpResponseBadRequest("参数不全")
        # 2.2 判断文章分类id数据是否正确
        try:
            article_category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest("没有此分类信息")
        # 3.处理数据--保存到数据库
        try:
            article = Article.objects.create(
                author=user,
                avatar=avatar,
                category=article_category,
                tags=tags,
                title=title,
                sumary=sumary,
                content=content
            )
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest("发布失败，请稍后再试")

        # 4.返回响应，跳转到文章详情页面（暂时跳转到首页）
        return redirect(reverse("home:index"))





