from django.contrib import admin
from .models import Product, Category


# Register your models here.
@admin.register(Product)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'price', 'stock')
