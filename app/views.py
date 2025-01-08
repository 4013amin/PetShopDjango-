from django.shortcuts import render, redirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from app.models import Product, Category, Favorite, OTP, ProductImage
from app.serializers import ProductSerializer, CategorySerializer, UsersSerializer, FavoriteSerializer
from rest_framework.permissions import IsAuthenticated
import random
from .models import OTP
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

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


# class AddProductView(APIView):
#     def post(self, request):
#         # دریافت داده‌ها از درخواست
#         data = request.data
#         base64_image = data.get('image')  # فرض بر این است که تصویر به صورت Base64 ارسال می‌شود
#
#         # اگر تصویر وجود دارد، آن را ذخیره می‌کنیم
#         if base64_image:
#             product = Product(
#                 name=data.get('name'),
#                 description=data.get('description'),
#                 nameUser=data.get('nameUser'),
#                 phone=data.get('phone'),
#                 city=data.get('city'),
#                 address=data.get('address'),
#                 family=data.get('family'),
#                 price=data.get('price'),
#             )
#             # ذخیره تصویر
#             product.save_image(base64_image)
#             product.save()
#
#             # بازگشت نتیجه
#             return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
#         else:
#             return Response({"error": "Image is required"}, status=status.HTTP_400_BAD_REQUEST)


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

        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()

            # ذخیره تصاویر به مدل ProductImage
            for image in images:
                ProductImage.objects.create(product=product, image=image)

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
        product_id = request.data.get('id')
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


OTP_EXPIRATION_TIME = 2 * 60


def generate_otp():
    return random.randint(10000, 99999)


@csrf_exempt
def send_otp(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone')
        if not phone_number:
            return JsonResponse({'status': 'error', 'message': 'Phone number is required.'}, status=400)

        otp = generate_otp()

        OTP.objects.create(phone=phone_number, otp=otp, is_valid=True)

        print(f"OTP for {phone_number}: {otp}")

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
