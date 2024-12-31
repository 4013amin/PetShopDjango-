from django.shortcuts import render, redirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from app.models import Product, Category, Favorite, OTP
from app.serializers import ProductSerializer, CategorySerializer, UsersSerializer, FavoriteSerializer
from rest_framework.permissions import IsAuthenticated
import random
import re
import time
from django.utils.timezone import now
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)


# Create your views here.
class GetProductsView(APIView):
    def get(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetProductByIdView(APIView):
    def get(self, request, pk):
        product = Product.objects.get(pk=pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddProductView(APIView):
    def post(self, request):
        # دریافت داده‌ها از درخواست
        data = request.data
        base64_image = data.get('image')  # فرض بر این است که تصویر به صورت Base64 ارسال می‌شود

        # اگر تصویر وجود دارد، آن را ذخیره می‌کنیم
        if base64_image:
            product = Product(
                name=data.get('name'),
                description=data.get('description'),
                nameUser=data.get('nameUser'),
                phone=data.get('phone'),
                city=data.get('city'),
                address=data.get('address'),
                family=data.get('family'),
                price=data.get('price'),
            )
            # ذخیره تصویر
            product.save_image(base64_image)
            product.save()

            # بازگشت نتیجه
            return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": "Image is required"}, status=status.HTTP_400_BAD_REQUEST)


class GetCategoriesView(APIView):
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddProductView(APIView):
    def post(self, request):
        print(request.data)  # Log request data
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddProfile(APIView):
    def post(self, request):
        serializer = UsersSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Favorite
class AddFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        try:
            product = Product.objects.get(id=product_id)
            favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)
            if created:
                return Response({"message": "Product added to favorites"}, status=status.HTTP_201_CREATED)
            return Response({"message": "Product already in favorites"}, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)


class RemoveFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        try:
            favorite = Favorite.objects.get(user=request.user, product_id=product_id)
            favorite.delete()
            return Response({"message": "Product removed from favorites"}, status=status.HTTP_200_OK)
        except Favorite.DoesNotExist:
            return Response({"error": "Favorite not found"}, status=status.HTTP_404_NOT_FOUND)


class GetFavoritesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorites = Favorite.objects.filter(user=request.user)
        serializer = FavoriteSerializer(favorites, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# زمان انقضا OTP (5 دقیقه)
OTP_EXPIRATION_TIME = 5 * 60  # 5 دقیقه بر حسب ثانیه


def generate_otp():
    return random.randint(10000, 99999)


@csrf_exempt
def send_otp(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone')
        if phone_number:
            otp = generate_otp()
            otp_sent_time = time.time() 

            otp_record = OTP.objects.create(
                phone=phone_number,
                otp=otp,
                created_at=otp_sent_time
            )

            print(f"OTP for {phone_number}: {otp}")  

            return JsonResponse({'message': 'OTP sent successfully'}, status=200)
        else:
            return JsonResponse({'error': 'Phone number is required'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')  # شماره تلفن
        otp_code = request.POST.get('otp')  # کد OTP

        # بررسی اینکه شماره تلفن و کد OTP ارسال شده‌اند
        if not phone or not otp_code:
            return JsonResponse({'status': 'error', 'message': 'Phone and OTP are required.'}, status=400)

        # پاک‌سازی شماره تلفن از هرگونه فاصله یا کاراکتر اضافی
        phone = phone.strip()

        # جستجو برای رکوردهای مرتبط با شماره تلفن
        otp_instances = OTP.objects.filter(phone=phone)

        if otp_instances.exists():
            # در صورتی که بیش از یک رکورد وجود داشته باشد، اولین رکورد را می‌گیرید
            otp_instance = otp_instances.first()

            # بررسی اینکه کد OTP ارسال شده با کد ذخیره‌شده در دیتابیس مطابقت دارد
            if otp_instance.otp == otp_code:
                # بررسی اینکه کد OTP منقضی نشده است (5 دقیقه)
                if now().timestamp() - otp_instance.created_at <= 5 * 60:
                    return JsonResponse({'status': 'success', 'message': 'OTP verified successfully.'}, status=200)
                else:
                    return JsonResponse({'status': 'error', 'message': 'Expired OTP.'}, status=400)
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid OTP.'}, status=400)
        else:
            # در صورتی که شماره تلفن در دیتابیس موجود نباشد
            return JsonResponse({'status': 'error', 'message': 'Phone number not found.'}, status=404)

    # اگر متد درخواست غیر از POST باشد
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

        
    
