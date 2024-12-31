from django.contrib import admin
from .models import Product, Category, Users ,OTP


# Register your models here.
@admin.register(Product)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'price')


@admin.register(Users)
class profileUsers(admin.ModelAdmin):
    list_display = ('phone', 'password')


@admin.register(OTP)
class OPTAdmin(admin.ModelAdmin):
    list_display = ('phone', 'otp')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
