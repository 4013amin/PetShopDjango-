from django.db import models


# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class OTP(models.Model):
    phone = models.CharField(max_length=15, unique=True)
    otp = models.CharField(max_length=5)
    is_valid = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.phone} - {self.otp}"


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    nameUser = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    family = models.CharField(max_length=255)
    image = models.ImageField(upload_to='products/images/', blank=True, null=True)
    price = models.PositiveIntegerField()
    user = models.ForeignKey(OTP, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"


class Profile(models.Model):
    user = models.OneToOneField(OTP, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='media/', blank=True, null=True)
    # gender = models.CharField(max_length=10, choices=[('male', 'مرد'), ('female', 'زن')], null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    phone = models.CharField(max_length=11 , null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.phone


#Chat
class ChatMessage(models.Model):
    sender = models.ForeignKey(OTP, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(OTP, related_name='received_messages', on_delete=models.CASCADE)
    message = models.TextField()
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, default='SENT', choices=[
            ('SENT', 'Sent'),
            ('DELIVERED', 'Delivered'),
            ('SEEN', 'Seen'),
        ])
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')

    def __str__(self):
        return f"{self.sender.phone} -> {self.receiver.phone}: {self.message[:20]}"