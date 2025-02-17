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
    image = models.ImageField(upload_to='profiles/images/', blank=True, null=True)
    credit = models.IntegerField(default=0)

    def __str__(self):
        return self.user.phone
