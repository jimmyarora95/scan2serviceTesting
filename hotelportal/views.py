from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from website.forms import StaffCreateForm
from .models import Room
from .forms import RoomForm
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db.models import Prefetch
from .forms import CategoryForm, ItemForm
from .models import Category, Item, ImageAsset
from django.db import IntegrityError, transaction










@login_required
def portal_home(request):
    # allow HOTEL_ADMIN or STAFF
    if getattr(request.user, "role", None) not in ("HOTEL_ADMIN", "STAFF", "PLATFORM_ADMIN"):
        return HttpResponseForbidden("Not allowed.")
    return render(request, "hotelportal/portal_home.html")



User = get_user_model()

def _is_portal_user(user):
    return getattr(user, "role", None) in ("HOTEL_ADMIN", "PLATFORM_ADMIN")

@login_required
def portal_settings(request):
    if not _is_portal_user(request.user) and request.user.role != "STAFF":
        return HttpResponseForbidden("Not allowed.")
    return render(request, "hotelportal/settings.html")

@login_required
def staff_list(request):
    if not _is_portal_user(request.user):
        return HttpResponseForbidden("Not allowed.")
    staff = User.objects.filter(hotel=request.user.hotel).order_by("username")
    return render(request, "hotelportal/staff_list.html", {"staff": staff})

@login_required
def staff_add(request):
    if getattr(request.user, "role", None) not in ("HOTEL_ADMIN", "PLATFORM_ADMIN"):
        return HttpResponseForbidden("Only hotel admins can add staff.")
    if request.method == "POST":
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.hotel = request.user.hotel  # bind to same hotel (critical)
            user.save()
            messages.success(request, f"Staff user “{user.username}” created.")
            return redirect("staff_list")
    else:
        form = StaffCreateForm()
    return render(request, "hotelportal/staff_add.html", {"form": form})


@login_required
def rooms_list(request):
    if not _is_portal_user(request.user) and request.user.role != "STAFF":
        return HttpResponseForbidden("Not allowed.")
    rooms = Room.objects.filter(hotel=request.user.hotel).order_by("floor", "number")
    return render(request, "hotelportal/rooms_list.html", {"rooms": rooms})


@login_required
def room_create(request):
    if not _is_portal_user(request.user):  # hotel admin or platform admin only
        return HttpResponseForbidden("Only hotel admins can add rooms.")
    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.hotel = request.user.hotel
            room.save()
            return redirect("rooms_list")
    else:
        form = RoomForm()
    return render(request, "hotelportal/room_form.html", {"form": form, "mode": "create"})


@login_required
def room_edit(request, pk):
    if not _is_portal_user(request.user):
        return HttpResponseForbidden("Only hotel admins can edit rooms.")
    room = get_object_or_404(Room, pk=pk, hotel=request.user.hotel)
    if request.method == "POST":
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            return redirect("rooms_list")
    else:
        form = RoomForm(instance=room)
    return render(request, "hotelportal/room_form.html", {"form": form, "mode": "edit", "room": room})



@login_required
@require_POST
def room_delete(request, pk):
    # Only hotel/platform admins can delete
    if not _is_portal_user(request.user):
        return HttpResponseForbidden("Only hotel admins can delete rooms.")
    room = get_object_or_404(Room, pk=pk, hotel=request.user.hotel)
    if room.current_stay:
        messages.error(request, "Cannot delete: room has an active stay. Check out first.")
        return redirect("rooms_list")
    number = room.number
    room.delete()  # CASCADE wipes related Stays (and later Requests)
    messages.success(request, f"Room {number} deleted permanently.")
    return redirect("rooms_list")


@login_required
def rooms_qr_sheet(request):
    # allow HOTEL_ADMIN, STAFF, PLATFORM_ADMIN to print
    if getattr(request.user, "role", None) not in ("HOTEL_ADMIN", "STAFF", "PLATFORM_ADMIN"):
        return HttpResponseForbidden("Not allowed.")
    hotel = request.user.hotel
    rooms = Room.objects.filter(hotel=hotel, is_active=True).order_by("floor", "number")
    context = {
        "hotel": hotel,
        "rooms": rooms,
        "SITE_URL": settings.SITE_URL,   # 🔸 (not in basic Django, but needed for Scan2Service)
    }
    return render(request, "hotelportal/rooms_qr_sheet.html", context)









# 4.2B — Catalog views


#this function is getting used twice..
def _is_admin(user):
    return getattr(user, "role", None) in ("HOTEL_ADMIN", "PLATFORM_ADMIN")

# Categories
@login_required
def categories_list(request):
    if not (_is_admin(request.user) or request.user.role == "STAFF"):
        return HttpResponseForbidden("Not allowed.")
    qs = Category.objects.filter(hotel=request.user.hotel).select_related("parent").order_by("kind","parent__name","position","name")
    return render(request, "hotelportal/categories_list.html", {"categories": qs})

@login_required
def category_create(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden("Only admins can add categories.")
    if not getattr(request.user, "hotel", None):
        return HttpResponseForbidden("Your user is not linked to a hotel.")

    if request.method == "POST":
        form = CategoryForm(request.POST, request=request)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.hotel = request.user.hotel          # ← ensure hotel is set
            cat.save()
            messages.success(request, "Category created.")
            return redirect("categories_list")
    else:
        form = CategoryForm(request=request)
    return render(request, "hotelportal/category_form.html", {"form": form, "mode": "create"})

# category_edit
@login_required
def category_edit(request, pk):
    if not _is_admin(request.user):
        return HttpResponseForbidden("Only admins can edit categories.")
    obj = get_object_or_404(Category, pk=pk, hotel=request.user.hotel)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=obj, request=request)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.hotel = request.user.hotel          # ← ensure hotel sticks
            cat.save()
            messages.success(request, "Category updated.")
            return redirect("categories_list")
    else:
        form = CategoryForm(instance=obj, request=request)
    return render(request, "hotelportal/category_form.html", {"form": form, "mode": "edit", "obj": obj})
@login_required
@require_POST
def category_delete(request, pk):
    if not _is_admin(request.user):
        return HttpResponseForbidden("Only admins can delete categories.")
    obj = get_object_or_404(Category, pk=pk, hotel=request.user.hotel)
    obj.delete()
    messages.success(request, "Category deleted.")
    return redirect("categories_list")

# Items
@login_required
def items_list(request):
    if not (_is_admin(request.user) or request.user.role == "STAFF"):
        return HttpResponseForbidden("Not allowed.")
    cat_id = request.GET.get("category")
    cats = Category.objects.filter(hotel=request.user.hotel, is_active=True).order_by("kind","position","name")
    items = Item.objects.filter(hotel=request.user.hotel).select_related("category","image").order_by("category__name","position","name")
    if cat_id:
        items = items.filter(category_id=cat_id)
    return render(request, "hotelportal/items_list.html", {"items": items, "categories": cats, "cat_id": cat_id})

@login_required
def item_create(request):
    if not _is_portal_user(request.user):
        return HttpResponseForbidden("Only admins can add items.")
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            item = form.save(commit=False)
            item.hotel = request.user.hotel                  # ← critical line
            if item.category.hotel_id != item.hotel_id:
                form.add_error("category", "Selected category belongs to a different hotel.")
            else:
                item.save()
                messages.success(request, "Item created.")
                return redirect("items_list")
    else:
        form = ItemForm(request=request)
    return render(request, "hotelportal/item_form.html", {"form": form, "mode": "create"})


@login_required
def item_edit(request, pk):
    if not _is_portal_user(request.user):
        return HttpResponseForbidden("Only admins can edit items.")
    obj = get_object_or_404(Item, pk=pk, hotel=request.user.hotel)
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=obj, request=request)
        if form.is_valid():
            item = form.save(commit=False)
            item.hotel = request.user.hotel                  # ← critical line
            if item.category.hotel_id != item.hotel_id:
                form.add_error("category", "Selected category belongs to a different hotel.")
            else:
                item.save()
                messages.success(request, "Item updated.")
                return redirect("items_list")
    else:
        form = ItemForm(instance=obj, request=request)
    return render(request, "hotelportal/item_form.html", {"form": form, "mode": "edit", "obj": obj})


@login_required
@require_POST
def item_delete(request, pk):
    if not _is_admin(request.user):
        return HttpResponseForbidden("Only admins can delete items.")
    obj = get_object_or_404(Item, pk=pk, hotel=request.user.hotel)
    obj.delete()
    messages.success(request, "Item deleted.")
    return redirect("items_list")

