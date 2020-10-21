from django.shortcuts import render
from django.views import View
from django.http import HttpResponseBadRequest, HttpResponse
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection


class RegisterView(View):
    """用户注册"""
    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, "register.html")


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
