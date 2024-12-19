import base64

from django.db import models
from django.core.files.base import ContentFile


# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    nameUser = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    family = models.CharField(max_length=255)
    image = models.ImageField(upload_to='products/images/')
    price = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save_image(self, base64_image: str):
        # Decode the base64 image string and save it as a file
        image_data = base64.b64decode(base64_image)
        image_name = 'image.jpg'  # You can generate a dynamic name
        image_file = ContentFile(image_data, name=image_name)
        self.image.save(image_name, image_file)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['product'], name='unique_product_images')
        ]


class Users(models.Model):
    phone = models.CharField(max_length=12)
    password = models.CharField(max_length=20)
