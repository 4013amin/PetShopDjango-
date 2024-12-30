from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from .views import GetProductsView, AddProductView, GetCategoriesView, GetProductByIdView, AddProfile, AddFavoriteView, \
    RemoveFavoriteView, GetFavoritesView

urlpatterns = [
                  path('getallProduct/', GetProductsView.as_view()),
                  path('products/<int:pk>/', GetProductByIdView.as_view()),
                  path('GetCategories/', GetCategoriesView.as_view()),
                  path('registerUser/', AddProfile.as_view()),
                  path('AddProduct/', AddProductView.as_view()),
                  path('favorites/add/', AddFavoriteView.as_view(), name='add_favorite'),
                  path('favorites/remove/', RemoveFavoriteView.as_view(), name='remove_favorite'),
                  path('favorites/', GetFavoritesView.as_view(), name='get_favorites'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
