from django.urls import path
from . import views

urlpatterns = [
    # main guest page
    path("h/<int:hotel_id>/r/<int:room_id>/", views.room_view, name="guest_room"),

    # cart (HTML fragments)
    path("h/<int:hotel_id>/r/<int:room_id>/cart/view/",   views.cart_view,   name="cart_view"),
    path("h/<int:hotel_id>/r/<int:room_id>/cart/add/",    views.cart_add,    name="cart_add"),
    path("h/<int:hotel_id>/r/<int:room_id>/cart/update/", views.cart_update, name="cart_update"),
    path("h/<int:hotel_id>/r/<int:room_id>/cart/clear/",  views.cart_clear,  name="cart_clear"),

    # submit (stub)
    path("h/<int:hotel_id>/r/<int:room_id>/order/submit/", views.order_submit_stub, name="order_submit_stub"),

# guest/urls.py (append these to your existing urlpatterns)

# Service "Request now" (no cart)
    path("h/<int:hotel_id>/r/<int:room_id>/service/request/", views.service_request, name="service_request"),

# Guest summary (orders & services combined)
    path("h/<int:hotel_id>/r/<int:room_id>/summary/", views.my_summary, name="guest_summary"),



]
