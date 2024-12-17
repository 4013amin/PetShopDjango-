from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from .views import GetProductsView, AddProductView, GetCategoriesView

urlpatterns = [
                  path('getallProduct', GetProductsView.as_view()),
                  path('GetCategories', GetCategoriesView.as_view()),
                  path('AddProduct', AddProductView.as_view()),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
