from django.shortcuts import render, redirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from app.models import Product, Category, Favorite, OTP, ProductImage
from app.serializers import ProductSerializer, CategorySerializer, UsersSerializer, FavoriteSerializer
import random
from .models import OTP
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
import requests

logger = logging.getLogger(__name__)


# Create your views here.
class GetProductsView(APIView):
    def get(self, request):
        products = Product.objects.prefetch_related('images').all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetProductByIdView(APIView):
    def get(self, request, pk):
        product = Product.objects.get(pk=pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetCategoriesView(APIView):
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddProductView(APIView):
    def post(self, request):
        images = request.FILES.getlist('images')

        if len(images) > 10:
            return Response(
                {"error": "You can upload a maximum of 10 images per product."},
                status=status.HTTP_400_BAD_REQUEST
            )

        phone = request.data.get('phone')  # فرض می‌کنیم شماره تلفن کاربر ارسال می‌شود
        try:
            user = OTP.objects.get(phone=phone)
        except OTP.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save(user=user)

            for image in images:
                ProductImage.objects.create(product=product, image=image)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProductsView(APIView):
    def get(self, request):
        phone = request.query_params.get('phone')

        if not phone:
            return Response({"error": "Phone not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = OTP.objects.get(phone=phone)
        except OTP.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        products = Product.objects.filter(user=user)

        serializer = ProductSerializer(products, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        phone = request.query_params.get('phone')
        id_Product = request.query_params.get('id')

        if not phone or not id_Product:
            return Response({"error": "Phone or Product ID is missing."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = OTP.objects.get(phone=phone)
        except OTP.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            product = Product.objects.get(user=user, id=int(id_Product))  # تبدیل به int
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        product.delete()
        return Response({"message": "Product deleted."}, status=status.HTTP_200_OK)


OTP_EXPIRATION_TIME = 2 * 60
SMS_IR_API_KEY = "PN1TVeBeaAehFLJAKU4XdfpsFXsQguYfleO0bV4ceh6diTZid2hRXza3uSkBbDef"


def generate_otp():
    return random.randint(10000, 99999)


# ارسال پیامک از طریق SMS.ir
def send_sms_ir(phone_number, otp):
    url = "https://api.sms.ir/v1/send/verify"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": SMS_IR_API_KEY
    }
    payload = {
        "mobile": phone_number,
        "templateId": "302699",  # شناسه قالب پیامک شما در پنل SMS.ir
        "parameters": [
            {"name": "OTP", "value": otp}  # متغیرهای موردنیاز در قالب پیامک
        ]
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return True
    else:
        raise Exception(f"SMS.ir Error: {response.text}")


@csrf_exempt
def send_otp(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone')
        if not phone_number:
            return JsonResponse({'status': 'error', 'message': 'Phone number is required.'}, status=400)

        # بررسی اینکه آیا شماره تلفن قبلاً ثبت‌نام کرده است یا خیر
        otp_entry = OTP.objects.filter(phone=phone_number).first()

        if otp_entry:
            # شماره تلفن قبلاً موجود است، فقط کد جدید ارسال می‌کنیم
            otp = generate_otp()
            otp_entry.otp = otp  # کد جدید را به OTP قبلی نسبت می‌دهیم
            otp_entry.is_valid = True  # دوباره کد را معتبر می‌کنیم
            otp_entry.save()

            print(f"OTP for {phone_number}: {otp}")
            try:
                send_sms_ir(phone_number, otp)
                return JsonResponse({'status': 'success', 'message': 'OTP sent successfully.'}, status=200)
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f"Error sending OTP: {str(e)}"}, status=500)
        else:
            # اگر شماره تلفن وجود نداشت، OTP جدید را ایجاد کرده و ذخیره می‌کنیم
            otp = generate_otp()
            OTP.objects.create(phone=phone_number, otp=otp, is_valid=True)

            print(f"OTP for {phone_number}: {otp}")
            try:
                send_sms_ir(phone_number, otp)
                return JsonResponse({'status': 'success', 'message': 'OTP sent successfully.'}, status=200)
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f"Error sending OTP: {str(e)}"}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        otp = request.POST.get('otp')

        # بررسی اینکه شماره تلفن و OTP وارد شده‌اند
        if not phone or not otp:
            return JsonResponse({'error': 'Phone number and OTP are required'}, status=400)

        try:
            print(f"Verifying OTP for phone: {phone}, OTP: {otp}")

            # تلاش برای پیدا کردن OTP مربوطه در پایگاه داده
            otp_entry = OTP.objects.get(phone=phone, otp=otp, is_valid=True)

            # بررسی اعتبار کد OTP
            if otp_entry.is_valid:
                return JsonResponse({'message': 'OTP already verified.'})

            # تأیید OTP و تغییر وضعیت آن
            otp_entry.is_valid = True
            otp_entry.is_valid = False  # تغییر وضعیت به غیرفعال پس از تأیید
            otp_entry.save()

            return JsonResponse({'message': 'OTP verified successfully!'}, status=200)

        except OTP.DoesNotExist:
            return JsonResponse({'error': 'Invalid OTP or phone number'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
