from django.contrib import admin
from .models import Product, Category, OTP, ProductImage, Profile


# Register your models here.
@admin.register(Product)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'price')


@admin.register(ProductImage)
class ImageFiledAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'image')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
