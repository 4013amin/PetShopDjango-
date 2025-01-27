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
        phone = request.query_params.get('phone')  # دریافت شماره تلفن کاربر از پارامترهای درخواست
        if not phone:
            return Response({"error": "Phone number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = OTP.objects.get(phone=phone)
        except OTP.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        products = Product.objects.filter(user=user)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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

        otp = generate_otp()

        OTP.objects.create(phone=phone_number, otp=otp, is_valid=True)

        print(f"OTP for {phone_number}: {otp}")

        # ارسال پیامک
        try:
            send_sms_ir(phone_number, otp)
            print(f"OTP sent to {phone_number}: {otp}")
            return JsonResponse({'status': 'success', 'message': 'OTP sent successfully.'}, status=200)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error sending OTP: {str(e)}"}, status=500)

        return JsonResponse({'status': 'success', 'message': 'OTP sent successfully.'}, status=200)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        otp = request.POST.get('otp')

        if not phone or not otp:
            return JsonResponse({'error': 'Phone number and OTP are required'}, status=400)

        try:
            print(f"Verifying OTP for phone: {phone}, OTP: {otp}")

            otp_entry = OTP.objects.get(phone=phone, otp=otp, is_valid=True)

            if otp_entry.is_valid:
                otp_entry.is_verified = True
                otp_entry.save()
                return JsonResponse({'message': 'OTP verified successfully!'})
            else:
                return JsonResponse({'error': 'OTP is expired'}, status=400)

        except OTP.DoesNotExist:
            return JsonResponse({'error': 'Invalid OTP or phone number'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
