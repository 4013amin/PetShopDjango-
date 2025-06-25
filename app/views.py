from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from app.models import Product, Category, ProductImage, Profile, ChatMessage
from app.serializers import ProductSerializer, CategorySerializer, ProfileSerializer, ChatUserSerializer
import random
from .models import OTP
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
from rest_framework.parsers import MultiPartParser, FormParser
import requests
from rest_framework.parsers import JSONParser
from google.cloud import vision
import io
import os

# SMS OTP
OTP_EXPIRATION_TIME = 2 * 60
SMS_IR_API_KEY = "fTisg3oGV8mUzxnKhr9a81XpbbTekqsa7Y2YYwdZ5S1X7GDi"

logger = logging.getLogger(__name__)


# Create your views here.
class GetProductsView(APIView):
    def get(self, request):
        products = Product.objects.prefetch_related('images').all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetProductByIdView(APIView):
    def get(self, _, pk):
        try:
            product = Product.objects.get(pk=pk)
            serializer = ProductSerializer(product)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            logger.warning(f"محصول با آیدی {pk} پیدا نشد.")
        return Response({"error": f"محصول با آیدی {pk} پیدا نشد."}, status=status.HTTP_404_NOT_FOUND)


class GetCategoriesView(APIView):
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path_to_your_key.json"


def is_pet_related_text(text):
    pet_keywords = [
        "سگ", "گربه", "پت", "حیوان", "ماهی", "پرنده", "خرگوش", "آکواریوم", "قلاده", "اسباب‌بازی", "بستر", "غذای حیوانات"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in pet_keywords)


def is_pet_related_image(image_file):
    vision_client = vision.ImageAnnotatorClient()
    content = image_file.read()
    image = vision.Image(content=content)

    response = vision_client.label_detection(image=image)
    labels = response.label_annotations

    pet_keywords = {
        "dog", "cat", "puppy", "kitten", "animal", "pet", "bird", "fish", "hamster", "leash", "cage", "aquarium",
        "parrot", "rabbit"
    }

    for label in labels:
        if label.description.lower() in pet_keywords:
            return True
    return False


class AddProductView(APIView):
    def post(self, request):
        images = request.FILES.getlist('images')

        if len(images) > 10:
            return Response(
                {"error": "You can upload a maximum of 10 images per product."},
                status=status.HTTP_400_BAD_REQUEST
            )


        phone = request.data.get('phone')
        if not phone:
            return Response({"error": "Phone number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = OTP.objects.get(phone=phone)
        except OTP.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        title = request.data.get('title', '')
        description = request.data.get('description', '')

        full_text = f"{title} {description}"
        if not is_pet_related_text(full_text):
            return Response({"error": "Product content must be related to pets."}, status=status.HTTP_400_BAD_REQUEST)

        for image in images:
            image.seek(0)
            if not is_pet_related_image(image):
                return Response({"error": "Uploaded image is not related to pets."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save(user=user)
            for image in images:
                image.seek(0)
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


def generate_otp():
    return random.randint(10000, 99999)


def send_sms_ir(phone_number, otp):
    url = "https://api.sms.ir/v1/send/verify"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": SMS_IR_API_KEY
    }
    payload = {
        "mobile": phone_number,
        "templateId": "302699",
        "parameters": [
            {"name": "OTP", "value": otp}
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

        otp_entry = OTP.objects.filter(phone=phone_number).first()

        if otp_entry:
            otp = generate_otp()
            otp_entry.otp = otp
            otp_entry.is_valid = True
            otp_entry.save()

            print(f"OTP for {phone_number}: {otp}")
            try:
                send_sms_ir(phone_number, otp)
                return JsonResponse({'status': 'success', 'message': 'OTP sent successfully.'}, status=200)
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f"Error sending OTP: {str(e)}"}, status=500)
        else:
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

        if not phone or not otp:
            return JsonResponse({'error': 'Phone number and OTP are required'}, status=400)

        try:
            print(f"Verifying OTP for phone: {phone}, OTP: {otp}")

            otp_entry = OTP.objects.get(phone=phone, otp=otp, is_valid=True)

            if otp_entry.is_valid:
                profile, created = Profile.objects.get_or_create(user=otp_entry)
                if created:
                    print(f"New profile created for user: {phone}")
                else:
                    print(f"Profile already exists for user: {phone}")

                return JsonResponse({'message': 'OTP verified successfully!'}, status=200)

        except OTP.DoesNotExist:
            return JsonResponse({'error': 'Invalid OTP or phone number'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


class ProfileView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request):
        phone = request.query_params.get('phone')

        if not phone:
            return Response(
                {"error": "Phone number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = OTP.objects.get(phone=phone)
            profile = Profile.objects.get_or_create(user=user)[0]
            serializer = ProfileSerializer(profile)

            total_users = OTP.objects.count()

            response_data = serializer.data
            response_data['total_users'] = total_users

            return Response(response_data, status=status.HTTP_200_OK)
        except OTP.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request):
        phone = request.query_params.get('phone')

        if not phone:
            return Response({"error": "This phone is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = OTP.objects.get(phone=phone)
            profile = Profile.objects.get_or_create(user=user)[0]

            if not profile.name and not profile.image:
                profile.name = request.data.get('name', profile.name)
                profile.image = request.FILES.get('image', profile.image)
                profile.bio = request.data.get('bio', profile.bio)
                profile.address = request.data.get('address', profile.address)
                profile.save()

            serializer = ProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except OTP.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        phone = request.query_params.get('phone')

        if not phone:
            return Response({"error": "This phone is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = OTP.objects.get(phone=phone)
            profile = Profile.objects.get(user=user)

            profile.delete()
            return Response({"message": f"Profile for {phone} deleted successfully."}, status=status.HTTP_200_OK)

        except OTP.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)


logger = logging.getLogger(__name__)


class ChatUsersView(APIView):
    def get(self, request):
        phone = request.query_params.get('phone')
        logger.info(f"Received phone: {phone}")

        if not phone:
            logger.warning("Phone number is missing in the request.")
            return Response({'error': 'Phone number required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            otp_user = OTP.objects.get(phone=phone)

            # دریافت شناسه‌های فرستنده‌هایی که به این کاربر پیام داده‌اند
            sender_ids = ChatMessage.objects.filter(receiver=otp_user) \
                .values_list('sender_id', flat=True).distinct()

            # دریافت شماره تلفن فرستنده‌ها
            users = OTP.objects.filter(id__in=sender_ids)

            # سریالایز کردن داده‌ها
            serializer = ChatUserSerializer(users, many=True)
            logger.info(f"Found chat users for phone {phone}: {serializer.data}")
            return Response({'users': serializer.data}, status=status.HTTP_200_OK)

        except OTP.DoesNotExist:
            logger.warning(f"Phone number {phone} not found in OTP model.")
            return Response({'error': 'Phone number not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching chat users: {str(e)}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Chat_DelelteView(APIView):
    def delete(self, request, sender, receiver):
        ChatMessage.objects.filter(
            sender__phone=sender,
            receiver__phone=receiver
        ).delete()

        ChatMessage.objects.filter(
            sender__phone=receiver,
            receiver__phone=sender
        ).delete()
        return Response({'message': 'Chat deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
