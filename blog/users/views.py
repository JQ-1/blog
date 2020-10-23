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
from django.contrib.auth import login, authenticate


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







