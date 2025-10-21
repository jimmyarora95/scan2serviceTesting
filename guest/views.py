# guest/views.py — Day-4: live cart with HTML fragments, phone gate OFF

from collections import defaultdict
from decimal import Decimal

from django.db import transaction, IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from hotelportal.models import Hotel, Room, Category, Item, Cart, CartItem, Request, RequestLine










# ---------- helpers ----------

def _get_or_create_cart(hotel, room, stay=None):
    """
    Day-4: we run without check-in, so 'stay' can be None.
    """
    cart, _ = Cart.objects.get_or_create(
        hotel=hotel, room=room, stay=stay, status="DRAFT"
    )
    return cart


def _badge_count(cart: Cart) -> int:
    return sum(ci.qty for ci in cart.items.all())


def _render_cart_fragment(cart: Cart) -> HttpResponse:
    items = list(cart.items.select_related("item"))
    total = sum((ci.price_snapshot * ci.qty for ci in items), Decimal("0.00"))

    html = render_to_string(
        "guest/_cart_body.html",
        {"cart": cart, "items": items, "total": total},
    )
    resp = HttpResponse(html)
    # send live badge count in header so JS can update the bubble
    resp["X-Cart-Count"] = str(_badge_count(cart))
    return resp


# ---------- main page ----------

from collections import defaultdict
from django.shortcuts import render, get_object_or_404

def room_view(request, hotel_id, room_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, status="ACTIVE")
    room = get_object_or_404(Room, id=room_id, hotel=hotel, is_active=True)

    # Categories and items (active/available)
    cats = (
        Category.objects
        .filter(hotel=hotel, is_active=True)
        .select_related("parent")
        .order_by("position", "name")
    )
    items = (
        Item.objects
        .filter(hotel=hotel, is_available=True)
        .select_related("category", "image")
        .order_by("position", "name")
    )

    # Group items by category id
    items_by_cat = defaultdict(list)
    for it in items:
        items_by_cat[it.category_id].append(it)

    # Build children map and top-level lists
    children = defaultdict(list)
    top_food, top_service = [], []
    for c in cats:
        if c.parent_id:
            children[c.parent_id].append(c)
        else:
            (top_food if c.kind == "FOOD" else top_service).append(c)

    # Cart for this room (Day-4: stay=None)
    cart = _get_or_create_cart(hotel, room, stay=None)

    # ⬇️ NEW: find service items that already have an open request (NEW/ACCEPTED) for this room
    open_service_ids = set(
        Request.objects
        .filter(
            hotel=hotel,
            room=room,
            kind="SERVICE",
            status__in=["NEW", "ACCEPTED"],
        )
        .exclude(service_item__isnull=True)
        .values_list("service_item_id", flat=True)
    )

    ctx = dict(
        hotel=hotel,
        room=room,
        top_food=top_food,
        top_service=top_service,
        children=children,
        items_by_cat=items_by_cat,
        cart_count=_badge_count(cart),
        open_service_ids=open_service_ids,  # ⬅️ used in template to disable buttons
    )
    return render(request, "guest/room.html", ctx)

# ---------- cart endpoints (HTML) ----------

@require_GET
def cart_view(request, hotel_id, room_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, status="ACTIVE")
    room = get_object_or_404(Room, id=room_id, hotel=hotel, is_active=True)
    cart = _get_or_create_cart(hotel, room, stay=None)
    return _render_cart_fragment(cart)


@require_POST
def cart_add(request, hotel_id, room_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, status="ACTIVE")
    room = get_object_or_404(Room, id=room_id, hotel=hotel, is_active=True)
    item_id = request.POST.get("item_id")
    qty = int(request.POST.get("qty", "1") or "1")
    if not item_id:
        return HttpResponseBadRequest("Missing item_id")
    if qty < 1:
        qty = 1

    item = get_object_or_404(Item, id=item_id, hotel=hotel, is_available=True)
    cart = _get_or_create_cart(hotel, room, stay=None)

    with transaction.atomic():
        ci, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            item=item,
            defaults={"qty": qty, "price_snapshot": item.price},
        )
        if not created:
            ci.qty += qty
            ci.save(update_fields=["qty"])
    return _render_cart_fragment(cart)


@require_POST
def cart_update(request, hotel_id, room_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, status="ACTIVE")
    room = get_object_or_404(Room, id=room_id, hotel=hotel, is_active=True)
    item_id = request.POST.get("item_id")
    qty = int(request.POST.get("qty", "1") or "1")
    if not item_id:
        return HttpResponseBadRequest("Missing item_id")

    cart = _get_or_create_cart(hotel, room, stay=None)
    ci = get_object_or_404(CartItem, cart=cart, item_id=item_id)
    if qty <= 0:
        ci.delete()
    else:
        ci.qty = qty
        ci.save(update_fields=["qty"])
    return _render_cart_fragment(cart)


@require_POST
def cart_clear(request, hotel_id, room_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, status="ACTIVE")
    room = get_object_or_404(Room, id=room_id, hotel=hotel, is_active=True)
    cart = _get_or_create_cart(hotel, room, stay=None)
    cart.items.all().delete()
    return _render_cart_fragment(cart)


@require_POST
def order_submit_stub(request, hotel_id, room_id):
    """
    Day-5: Convert DRAFT cart -> Request(kind=FOOD, status=NEW) + RequestLines,
    clear the cart, mark cart SUBMITTED. Returns JSON {ok: true, request_id}.
    """
    hotel = get_object_or_404(Hotel, id=hotel_id, status="ACTIVE")
    room  = get_object_or_404(Room, id=room_id, hotel=hotel, is_active=True)

    cart = Cart.objects.filter(hotel=hotel, room=room, status="DRAFT").first()
    if not cart or not cart.items.exists():
        return JsonResponse({"ok": False, "error": "empty_cart"}, status=400)

    with transaction.atomic():
        # compute subtotal
        subtotal = Decimal("0.00")
        for ci in cart.items.all():
            subtotal += ci.price_snapshot * ci.qty

        # create request (stay=None for now)
        req = Request.objects.create(
            hotel=hotel, room=room, stay=None,
            kind="FOOD", status="NEW", subtotal=subtotal
        )

        # lines with snapshots
        lines = []
        for ci in cart.items.select_related("item"):
            lines.append(RequestLine(
                request=req,
                item=ci.item,
                name_snapshot=ci.item.name,
                price_snapshot=ci.price_snapshot,
                qty=ci.qty,
                line_total=ci.price_snapshot * ci.qty,
            ))
        RequestLine.objects.bulk_create(lines)

        # clear cart
        cart.items.all().delete()
        cart.status = "SUBMITTED"
        cart.save(update_fields=["status"])

    return JsonResponse({"ok": True, "request_id": req.id})






@require_POST
def service_request(request, hotel_id, room_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, status="ACTIVE")
    room  = get_object_or_404(Room, id=room_id, hotel=hotel, is_active=True)

    item_id = request.POST.get("item_id")
    if not item_id:
        return HttpResponseBadRequest("Missing item_id")

    item = get_object_or_404(Item, id=item_id, hotel=hotel, is_available=True)
    if item.category.kind != "SERVICE":
        return JsonResponse({"ok": False, "error": "not_a_service"}, status=400)

    # Block duplicates: same room & service item with open status
    open_exists = Request.objects.filter(
        hotel=hotel, room=room, kind="SERVICE",
        service_item=item, status__in=["NEW", "ACCEPTED"]
    ).exists()
    if open_exists:
        return JsonResponse({"ok": False, "error": "already_requested"}, status=409)

    price = item.price if item.price is not None else Decimal("0.00")
    req = Request.objects.create(
        hotel=hotel, room=room, stay=None,
        kind="SERVICE", status="NEW", subtotal=price,
        note=item.name, service_item=item
    )
    return JsonResponse({"ok": True, "request_id": req.id})









@require_GET
def my_summary(request, hotel_id, room_id):
    """
    Return combined FOOD (lines) and SERVICE (notes) for this room.
    JSON shape tailored to the modal we built.
    """
    hotel = get_object_or_404(Hotel, id=hotel_id, status="ACTIVE")
    room  = get_object_or_404(Room, id=room_id, hotel=hotel, is_active=True)

    # recent first; you can add date range later
    reqs = Request.objects.filter(hotel=hotel, room=room).select_related().order_by("-created_at")[:50]

    food = []
    services = []
    for r in reqs:
        if r.kind == "FOOD":
            for ln in r.lines.select_related("item"):
                food.append({
                    "request_id": r.id,
                    "name": ln.name_snapshot,
                    "qty": ln.qty,
                    "price": float(ln.price_snapshot),
                    "status": r.status,
                    "ts": r.created_at.isoformat(),
                })
        else:
            # show the service name via note
            services.append({
                "request_id": r.id,
                "name": r.note or "Service",
                "qty": 1,
                "price": float(r.subtotal or 0),
                "status": r.status,
                "ts": r.created_at.isoformat(),
            })

    return JsonResponse({"food": food, "services": services})

