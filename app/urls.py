from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from . import views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title="PET Shop API",
        default_version='v1',
        description="API documentation for the project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="your-email@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
                  path('getallProduct/', views.GetProductsView.as_view()),
                  path('products/<int:pk>/', views.GetProductByIdView.as_view()),
                  path('GetCategories/', views.GetCategoriesView.as_view()),
                  path('user-products/', views.UserProductsView.as_view(), name="user-products"),
                  path('profile/', views.ProfileView.as_view()),
                  path('AddProduct/', views.AddProductView.as_view()),
                  path('send-otp/', views.send_otp, name='send_otp'),
                  path('verify-otp/', views.verify_otp, name='verify_otp'),

                  path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
                  path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
              
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
