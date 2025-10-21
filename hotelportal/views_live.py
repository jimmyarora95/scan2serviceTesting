# Day 5.3 — Staff Live Board (polling), with detail popup and today counters.

import json
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Request

def _allow_portal(user):
    return getattr(user, "role", None) in ("HOTEL_ADMIN", "STAFF", "PLATFORM_ADMIN")

def _hotel_or_403(request):
    hotel = getattr(request.user, "hotel", None)
    if not hotel and getattr(request.user, "role", None) != "PLATFORM_ADMIN":
        return None
    return hotel

def _serialize_requests(qs):
    """
    Convert Requests to JSON-serializable dicts for the board.
    """
    data = []
    # Prefetch lines only when needed to reduce queries.
    for r in qs:
        lines = []
        if r.kind == "FOOD":
            # show only a few lines for card; detail view shows all
            for ln in r.lines.all()[:4]:
                lines.append({"name": ln.name_snapshot, "qty": ln.qty})
        data.append({
            "id": r.id,
            "room": getattr(r.room, "number", ""),
            "kind": r.kind,                           # FOOD | SERVICE
            "status": r.status,                       # NEW | ACCEPTED (board shows only these)
            "subtotal": float(r.subtotal or 0),
            "created_at": r.created_at.isoformat(),
            "accepted_at": r.accepted_at.isoformat() if r.accepted_at else None,
            "lines": lines,                           # [] for service
            "note": r.note or "",
        })
    return data

@login_required
@user_passes_test(_allow_portal)
def live_board(request):
    """
    Render the Live Board page. We embed initial JSON safely and start polling.
    Only NEW and ACCEPTED are shown on the board; COMPLETED/CANCELLED are counted for today.
    """
    hotel = _hotel_or_403(request)
    if not hotel and request.user.role != "PLATFORM_ADMIN":
        return HttpResponseForbidden("No hotel set")

    qs = Request.objects.all()
    if hotel:
        qs = qs.filter(hotel=hotel)

    new_qs = qs.filter(status="NEW").select_related("room").order_by("-created_at")[:100]
    acc_qs = qs.filter(status="ACCEPTED").select_related("room").order_by("-updated_at")[:100]

    today = timezone.localdate()
    completed_today = qs.filter(status="COMPLETED", completed_at__date=today).count()
    cancelled_today = qs.filter(status="CANCELLED", cancelled_at__date=today).count()

    # IMPORTANT: dump to JSON strings so the template injects valid JS
    new_initial_json = json.dumps(_serialize_requests(new_qs))
    acc_initial_json = json.dumps(_serialize_requests(acc_qs))

    ctx = {
        "new_initial_json": new_initial_json,
        "accepted_initial_json": acc_initial_json,
        "completed_today": completed_today,
        "cancelled_today": cancelled_today,
    }
    return render(request, "hotelportal/live_board.html", ctx)

@login_required
@user_passes_test(_allow_portal)
def live_poll(request):
    """
    Return full snapshots of NEW and ACCEPTED every 8s + today's counters.
    """
    hotel = _hotel_or_403(request)
    if not hotel and request.user.role != "PLATFORM_ADMIN":
        return JsonResponse({"error": "no_hotel"}, status=403)

    qs = Request.objects.all()
    if hotel:
        qs = qs.filter(hotel=hotel)

    new_qs = qs.filter(status="NEW").select_related("room").order_by("-created_at")[:100]
    acc_qs = qs.filter(status="ACCEPTED").select_related("room").order_by("-updated_at")[:100]

    today = timezone.localdate()
    data = {
        "new": _serialize_requests(new_qs),
        "accepted": _serialize_requests(acc_qs),
        "counts": {
            "completed_today": qs.filter(status="COMPLETED", completed_at__date=today).count(),
            "cancelled_today": qs.filter(status="CANCELLED", cancelled_at__date=today).count(),
        }
    }
    return JsonResponse(data)

@login_required
@user_passes_test(_allow_portal)
def live_action(request, request_id):
    """
    POST: accept | complete | cancel
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    hotel = _hotel_or_403(request)
    if not hotel and request.user.role != "PLATFORM_ADMIN":
        return JsonResponse({"ok": False, "error": "no_hotel"}, status=403)

    action = request.POST.get("action")
    if action not in ("accept", "complete", "cancel"):
        return HttpResponseBadRequest("Invalid action")

    # lock the row to avoid race conditions
    qs = Request.objects.select_for_update()
    if hotel:
        qs = qs.filter(hotel=hotel)
    req = get_object_or_404(qs, id=request_id)

    now = timezone.now()
    if action == "accept":
        if req.status != "NEW":
            return JsonResponse({"ok": False, "error": "bad_state"}, status=409)
        req.status = "ACCEPTED"
        req.accepted_at = now
        req.save(update_fields=["status", "accepted_at", "updated_at"])
    elif action == "complete":
        if req.status != "ACCEPTED":
            return JsonResponse({"ok": False, "error": "bad_state"}, status=409)
        req.status = "COMPLETED"
        req.completed_at = now
        req.save(update_fields=["status", "completed_at", "updated_at"])
    else:  # cancel
        if req.status not in ("NEW", "ACCEPTED"):
            return JsonResponse({"ok": False, "error": "bad_state"}, status=409)
        req.status = "CANCELLED"
        req.cancelled_at = now
        req.save(update_fields=["status", "cancelled_at", "updated_at"])

    return JsonResponse({"ok": True})

@login_required
@user_passes_test(_allow_portal)
def live_detail(request, request_id):
    """
    Return an HTML fragment with full details for popup.
    """
    hotel = _hotel_or_403(request)
    if not hotel and request.user.role != "PLATFORM_ADMIN":
        return JsonResponse({"error": "no_hotel"}, status=403)
    qs = Request.objects.select_related("room").prefetch_related("lines")
    if hotel:
        qs = qs.filter(hotel=hotel)
    r = get_object_or_404(qs, id=request_id)
    html = render_to_string("hotelportal/_request_detail.html", {"r": r})
    return JsonResponse({"ok": True, "html": html})

@login_required
@user_passes_test(_allow_portal)
def history_stub(request):
    return HttpResponse("History page coming soon…")
