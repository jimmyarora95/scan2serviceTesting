from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.S2SLoginView.as_view(), name="login"),
    #path("logout/", views.S2SLogoutView.as_view(), name="logout"),
    path("logout/", views.signout, name="logout"),   # use our explicit view
]
