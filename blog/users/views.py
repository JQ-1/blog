from django.shortcuts import render
from django.views import View
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from utils.response_code import RETCODE
import logging
logger = logging.getLogger("django")
from random import randint
from libs.yuntongxun.sms import CCP


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
