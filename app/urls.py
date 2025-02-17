from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from . import views

urlpatterns = [
                  path('getallProduct/', views.GetProductsView.as_view()),
                  path('products/<int:pk>/', views.GetProductByIdView.as_view()),
                  path('GetCategories/', views.GetCategoriesView.as_view()),
                  path('user-products/', views.UserProductsView.as_view(), name="user-products"),
                  path('profile/', views.ProfileView.as_view()),
                  path('AddProduct/', views.AddProductView.as_view()),
                  path('send-otp/', views.send_otp, name='send_otp'),
                  path('verify-otp/', views.verify_otp, name='verify_otp'),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
