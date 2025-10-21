from django.contrib import admin
from .models import Room, Stay, Request, RequestLine, Category, ImageAsset, Item   






@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("hotel","number","floor","is_active","current_stay")
    list_filter  = ("hotel","is_active")
    search_fields = ("number",)

@admin.register(Stay)
class StayAdmin(admin.ModelAdmin):
    list_display = ("hotel","room","guest_name","phone","status","check_in_at","check_out_at","running_total")
    list_filter  = ("hotel","status")
    search_fields = ("guest_name","phone")
    readonly_fields = ("check_in_at","check_out_at")





# ----------------------------
# 4.1B — Catalog admin
# ----------------------------


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "parent", "hotel", "position", "is_active")
    list_filter = ("kind", "is_active", "hotel")
    search_fields = ("name",)
    ordering = ("hotel", "kind", "position", "name")

@admin.register(ImageAsset)
class ImageAssetAdmin(admin.ModelAdmin):
    list_display = ("name", "hotel", "created_at")
    list_filter = ("hotel",)
    search_fields = ("name", "tags")

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "hotel", "price", "unit", "is_available", "position")
    list_filter = ("category__kind", "is_available", "hotel", "category")
    search_fields = ("name", "description")
    ordering = ("hotel", "category", "position", "name")






# 5.1 — Admin for Request & RequestLine


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("id", "hotel", "room", "kind", "status", "subtotal", "created_at")
    list_filter  = ("hotel", "kind", "status", "created_at")
    search_fields = ("room__number", "id", "note")
    date_hierarchy = "created_at"
    autocomplete_fields = ("hotel", "room", "stay")
    ordering = ("-created_at",)

@admin.register(RequestLine)
class RequestLineAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "item", "name_snapshot", "price_snapshot", "qty", "line_total")
    list_filter  = ("item__hotel",)
    search_fields = ("name_snapshot", "request__id")
    autocomplete_fields = ("request", "item")
