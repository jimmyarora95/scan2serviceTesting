from django.urls import path
from . import views
from django.urls import path
from . import views_live  # NEW file below





urlpatterns = [
    path("", views.portal_home, name="portal_home"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/add/", views.staff_add, name="staff_add"),

     # rooms (Day 3.1)
    path("rooms/", views.rooms_list, name="rooms_list"),
    path("rooms/add/", views.room_create, name="room_create"),
    path("rooms/<int:pk>/edit/", views.room_edit, name="room_edit"),
    path("rooms/<int:pk>/delete/", views.room_delete, name="room_delete"),
    path("rooms/qr/print/", views.rooms_qr_sheet, name="rooms_qr_sheet"),
    # 3.3C — Settings route
    path("settings/", views.portal_settings, name="portal_settings"),
    # 4.2C — Catalog routes
    path("settings/categories/", views.categories_list, name="categories_list"),
    path("settings/categories/add/", views.category_create, name="category_create"),
    path("settings/categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("settings/categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("settings/items/", views.items_list, name="items_list"),
    path("settings/items/add/", views.item_create, name="item_create"),
    path("settings/items/<int:pk>/edit/", views.item_edit, name="item_edit"),
    path("settings/items/<int:pk>/delete/", views.item_delete, name="item_delete"),


    # --- Live Board (relative paths; project urls.py prefixes with 'portal/') ---
    path("live/", views_live.live_board, name="live_board"),
    path("live/poll/", views_live.live_poll, name="live_poll"),
    path("live/<int:request_id>/action/", views_live.live_action, name="live_action"),
    path("live/<int:request_id>/detail/", views_live.live_detail, name="live_detail"),

    # History page (stub for now)
    path("requests/history/", views_live.history_stub, name="portal_requests_history"),

]

