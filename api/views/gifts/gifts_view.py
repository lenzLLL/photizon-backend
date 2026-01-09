from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from api.models import BookOrder, ChurchAdmin, Content, Donation, DonationCategory, Church, User, TicketType
from api.serializers import BookOrderSerializer, DonationSerializer, DonationCategorySerializer, TicketSerializer
from api.permissions import IsAuthenticatedUser, user_is_church_owner

# ----------------------
# DonationCategory CRUD
# ----------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_categories_d(request):
    categories = DonationCategory.objects.all()
    serializer = DonationCategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_category_d(request):
    serializer = DonationCategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def retrieve_category_d(request, category_id):
    category = get_object_or_404(DonationCategory, id=category_id)
    serializer = DonationCategorySerializer(category)
    return Response(serializer.data)

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_category_d(request, category_id):
    category = get_object_or_404(DonationCategory, id=category_id)
    serializer = DonationCategorySerializer(category, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_category_d(request, category_id):
    category = get_object_or_404(DonationCategory, id=category_id)
    category.delete()
    return Response({"detail": "Category deleted"}, status=204)

# ----------------------
# Donations CRUD & Stats
# ----------------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def make_donation(request, church_id):
    church = get_object_or_404(Church, id=church_id)
    category_id = request.data.get("category")
    if user_is_church_owner(request.user, church):
        return Response({"error": "Church owners cannot make donations to their own church."}, status=403)
    category = None
    if category_id:
        category = get_object_or_404(DonationCategory, id=category_id)

    amount = request.data.get("amount")
    gateway = request.data.get("gateway", "CASH")
    message = request.data.get("message", "")

    if not amount:
        return Response({"error": "Amount is required"}, status=400)

    donation = Donation.objects.create(
        user=request.user,
        church=church,
        category=category,
        amount=amount,
        gateway=gateway,
        message=message
    )

    # Auto-confirm cash donations

    serializer = DonationSerializer(donation)
    return Response(serializer.data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_user_donations(request):
    donations = Donation.objects.filter(user=request.user).order_by("-created_at")
    serializer = DonationSerializer(donations, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_church_donations(request, church_id, include_subchurches=False):
    """
    Liste des dons pour une église.
    Si include_subchurches=True, inclut les sous-églises
    """
    church = get_object_or_404(Church, id=church_id)
    qs = Donation.objects.filter(church__in=[church.id])

    if include_subchurches:
        sub_ids = church.sub_churches.all().values_list("id", flat=True)
        qs = Donation.objects.filter(church__id__in=[church.id, *sub_ids])

    serializer = DonationSerializer(qs.order_by("-created_at"), many=True)
    return Response(serializer.data)


# ----------------------
# Stats par église
# ----------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def church_donation_stats(request, church_id, include_subchurches=True):
    """
    Retourne les stats pour une église :
    - total général
    - total par mois
    - total par année
    """
    church = get_object_or_404(Church, id=church_id)
    qs = Donation.objects.filter(church=church)

    if include_subchurches:
        sub_ids = church.sub_churches.all().values_list("id", flat=True)
        qs = Donation.objects.filter(church__id__in=[church.id, *sub_ids])

    total_sum = qs.aggregate(total=Sum("amount"))["total"] or 0

    # Stats par mois
    monthly = {}
    for i in range(12):
        month_start = timezone.now() - relativedelta(months=i)
        month_qs = qs.filter(
            created_at__year=month_start.year,
            created_at__month=month_start.month
        )
        monthly[f"{month_start.year}-{month_start.month:02d}"] = month_qs.aggregate(sum=Sum("amount"))["sum"] or 0

    # Stats par année
    years = qs.dates("created_at", "year")
    yearly = {}
    for y in years:
        year_qs = qs.filter(created_at__year=y.year)
        yearly[str(y.year)] = year_qs.aggregate(sum=Sum("amount"))["sum"] or 0

    return Response({
        "church_id": church.id,
        "church_title": church.title,
        "total_sum": total_sum,
        "monthly": monthly,
        "yearly": yearly
    })


# ----------------------
# Admin stats : toutes les églises
# ----------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_all_churches_donation_stats(request):
    """
    Retourne stats pour toutes les églises :
    - somme totale par église
    - stats mensuelles / annuelles par église
    - somme générale
    - grand total mensuel et annuel toutes églises
    """
    all_churches = Church.objects.all()
    result = []
    grand_total = 0

    # Préparer les périodes pour les 12 derniers mois
    now = timezone.now()
    last_12_months = [(now - relativedelta(months=i)).replace(day=1) for i in range(12)]
    monthly_totals_all_churches = {d.strftime("%Y-%m"): 0 for d in last_12_months}

    # Préparer années existantes pour les dons
    all_years = Donation.objects.dates("created_at", "year")
    yearly_totals_all_churches = {y.year: 0 for y in all_years}

    for church in all_churches:
        # Inclure les sous-églises
        qs = Donation.objects.filter(
            church__in=[church.id, *church.sub_churches.all().values_list("id", flat=True)]
        )
        total_sum = qs.aggregate(total=Sum("amount"))["total"] or 0
        grand_total += total_sum

        # Stats mensuelles par église
        monthly = {}
        for d in last_12_months:
            month_qs = qs.filter(created_at__year=d.year, created_at__month=d.month)
            month_sum = month_qs.aggregate(sum=Sum("amount"))["sum"] or 0
            monthly[d.strftime("%Y-%m")] = month_sum
            monthly_totals_all_churches[d.strftime("%Y-%m")] += month_sum  # cumul global

        # Stats annuelles par église
        yearly = {}
        for y in all_years:
            year_qs = qs.filter(created_at__year=y.year)
            year_sum = year_qs.aggregate(sum=Sum("amount"))["sum"] or 0
            yearly[str(y.year)] = year_sum
            yearly_totals_all_churches[y.year] += year_sum  # cumul global

        result.append({
            "church_id": church.id,
            "church_title": church.title,
            "total_sum": total_sum,
            "monthly": monthly,
            "yearly": yearly
        })

    return Response({
        "grand_total": grand_total,
        "churches": result,
        "monthly_totals_all_churches": monthly_totals_all_churches,
        "yearly_totals_all_churches": yearly_totals_all_churches
    })

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def admin_book_order_stats(request):
    all_orders = BookOrder.objects.select_related("content", "user").order_by("-created_at")

    grand_total = all_orders.aggregate(total=Sum("total_price"))["total"] or 0

    # Total par mois (12 derniers mois)
    monthly_totals = {}
    for i in range(12):
        month_start = timezone.now() - relativedelta(months=i)
        month_sum = all_orders.filter(
            created_at__year=month_start.year,
            created_at__month=month_start.month
        ).aggregate(sum=Sum("total_price"))["sum"] or 0
        monthly_totals[f"{month_start.year}-{month_start.month:02d}"] = month_sum

    # Total par année
    years = all_orders.dates("created_at", "year")
    yearly_totals = {}
    for y in years:
        yearly_sum = all_orders.filter(created_at__year=y.year).aggregate(sum=Sum("total_price"))["sum"] or 0
        yearly_totals[str(y.year)] = yearly_sum

    # Stats par livre
    book_stats = []
    books = Content.objects.filter(type="BOOK")
    for book in books:
        book_orders = all_orders.filter(content=book)
        total_sum = book_orders.aggregate(total=Sum("total_price"))["total"] or 0
        book_stats.append({
            "book_id": book.id,
            "title": book.title,
            "total_sum": total_sum
        })

    return Response({
        "grand_total": grand_total,
        "monthly_totals": monthly_totals,
        "yearly_totals": yearly_totals,
        "book_stats": book_stats
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_book_order(request, book_id):
    content = get_object_or_404(Content, id=book_id)
    order_type = request.data.get("delivery_type", "DIGITAL")  # DIGITAL ou PHYSICAL
    quantity = int(request.data.get("quantity", 1))
    # Ticket-related params
    is_ticket = bool(request.data.get("is_ticket", False))
    ticket_type_id = request.data.get("ticket_type_id")
    shipped = True if order_type.upper() == "DIGITAL" else False
    delivery_at = timezone.now() if shipped else None
    if user_is_church_owner(request.user, content.church):
        return Response({"error": "Church owners cannot order their own books."}, status=403)
    # If this is a ticket order, enforce event type and availability
    if is_ticket:
        if content.type != "EVENT":
            return Response({"error": "Tickets can only be purchased for EVENTS."}, status=400)

    order_kwargs = dict(
        user=request.user,
        content=content,
        quantity=quantity,
        delivery_type=order_type.upper(),
        shipped=shipped,
        delivered_at=delivery_at,
    )
    if is_ticket:
        order_kwargs["is_ticket"] = True
        if ticket_type_id:
            tt = get_object_or_404(TicketType, id=ticket_type_id)
            order_kwargs["ticket_type"] = tt

    order = BookOrder.objects.create(**order_kwargs)

    serializer = BookOrderSerializer(order)
    return Response(serializer.data, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_book_order(request, order_id):
    """Finalize a book/ticket order after payment confirmation.
    Expects `payment_transaction_id` in body. For ticket orders, this will call `issue_tickets()`.
    """
    order = get_object_or_404(BookOrder, id=order_id)
    payment_tx = request.data.get("payment_transaction_id")

    if not payment_tx:
        return Response({"error": "payment_transaction_id required"}, status=400)

    # Attach payment tx and if ticket order, issue tickets
    if order.is_ticket:
        try:
            tickets = order.issue_tickets(payment_transaction_id=payment_tx, buyer=request.user)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
        # serialize tickets
        ticket_serializer = TicketSerializer(tickets, many=True)
        return Response({"order": BookOrderSerializer(order).data, "tickets": ticket_serializer.data})

    # non-ticket orders: just attach payment id
    order.payment_transaction_id = payment_tx
    order.save()
    return Response(BookOrderSerializer(order).data)

# -----------------------------------------
# Lister les commandes d’un utilisateur
# -----------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_book_orders(request):
    orders = BookOrder.objects.filter(user=request.user).order_by("-created_at")
    serializer = BookOrderSerializer(orders, many=True)
    return Response(serializer.data)


# -----------------------------------------
# Détails / mise à jour d’une commande
# -----------------------------------------
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def book_order_detail(request, order_id):
    order = get_object_or_404(BookOrder, id=order_id)

    if request.method == "GET":
        serializer = BookOrderSerializer(order)
        return Response(serializer.data)

    if request.method == "PATCH":
        serializer = BookOrderSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def church_financial_overview(request, church_id):
    from django.db.models import Sum
    from django.utils.timezone import now

    # Vérifier que l'église existe
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response({"error": "Cette église n'existe pas."}, status=404)

    # 📌 Membres = Users dont current_church = church
    member_users = User.objects.filter(current_church=church)

    # ==========================
    #   1. ORDERS DES MEMBRES
    # ==========================

    member_orders = BookOrder.objects.filter(
        user__in=member_users,
        content__church=church
    ).select_related("user", "content")

    # ==========================
    #   2. DONATIONS DES MEMBRES
    # ==========================

    member_donations = Donation.objects.filter(
        user__in=member_users,
        church=church
    ).select_related("user", "category")

    # ==========================
    #   3. ORDERS NON MEMBRES
    # ==========================

    external_orders = BookOrder.objects.filter(
        content__church=church
    ).exclude(user__in=member_users)

    # ==========================
    #   4. DONATIONS NON MEMBRES
    # ==========================

    external_donations = Donation.objects.filter(
        church=church
    ).exclude(user__in=member_users)

    # ==============================================
    #   CALCUL DES TOTAUX (MENSUELS / ANNUELS / GLOBAL)
    # ==============================================

    current_month = now().month
    current_year = now().year

    def summarize(qs):
        return {
            "month": qs.filter(created_at__month=current_month).aggregate(total=Sum("amount"))["total"] or 0,
            "year": qs.filter(created_at__year=current_year).aggregate(total=Sum("amount"))["total"] or 0,
            "total": qs.aggregate(total=Sum("amount"))["total"] or 0,
            "withdrawed": qs.filter(withdrawed=True).aggregate(total=Sum("amount"))["total"] or 0,
            "pending_withdrawal": qs.filter(withdrawed=False).aggregate(total=Sum("amount"))["total"] or 0,
        }

    def summarize_orders(qs):
        return {
            "month": qs.filter(created_at__month=current_month).aggregate(total=Sum("total_price"))["total"] or 0,
            "year": qs.filter(created_at__year=current_year).aggregate(total=Sum("total_price"))["total"] or 0,
            "total": qs.aggregate(total=Sum("total_price"))["total"] or 0,
            "withdrawed": qs.filter(withdrawed=True).aggregate(total=Sum("total_price"))["total"] or 0,
            "pending_withdrawal": qs.filter(withdrawed=False).aggregate(total=Sum("total_price"))["total"] or 0,
        }

    # =============================
    #   SÉRIALISATION SIMPLE
    # =============================

    def serialize_order(o):
        return {
            "id": o.id,
            "user": o.user.phone_number,
            "content": o.content.title,
            "delivery_type": o.delivery_type,
            "total_price": o.total_price,
            "quantity": o.quantity,
            "withdrawed": o.withdrawed,
            "shipped": o.shipped,
            "delivered_at": o.delivered_at,
            "created_at": o.created_at,
        }

    def serialize_donation(d):
        return {
            "id": d.id,
            "user": d.user.phone_number,
            "amount": d.amount,
            "withdrawed": d.withdrawed,
            "category": d.category.name if d.category else None,
            "gateway": d.gateway,
            "created_at": d.created_at,
        }

    # =============================
    #   REPONSE FINALE
    # =============================

    return Response({
        "members": {
            "orders": {
                "items": [serialize_order(o) for o in member_orders],
                "summary": summarize_orders(member_orders)
            },
            "donations": {
                "items": [serialize_donation(d) for d in member_donations],
                "summary": summarize(member_donations)
            }
        },
        "non_members": {
            "orders": {
                "items": [serialize_order(o) for o in external_orders],
                "summary": summarize_orders(external_orders)
            },
            "donations": {
                "items": [serialize_donation(d) for d in external_donations],
                "summary": summarize(external_donations)
            }
        }
    })

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def withdraw_all_donations_view(request, church_id):
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response({"detail": "Church not found"}, status=404)

    # Vérifier que l’utilisateur est admin de cette église
    if not ChurchAdmin.objects.filter(church=church, user=request.user).exists():
        return Response({"detail": "Not authorized"}, status=403)

    donations = Donation.objects.filter(church=church, withdrawed=False)

    # Mise à jour en masse
    donations.update(withdrawed=True)

    return Response({
        "message": "Toutes les donations ont été retirées avec succès",
        "count": donations.count(),
    })

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def withdraw_all_orders_view(request, church_id):
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response({"detail": "Church not found"}, status=404)

    # Vérifier que l’utilisateur est admin de cette église
    if not ChurchAdmin.objects.filter(church=church, user=request.user).exists():
        return Response({"detail": "Not authorized"}, status=403)

    orders = BookOrder.objects.filter(content__church=church, withdrawed=False)

    # Mise à jour en masse
    orders.update(withdrawed=True)

    return Response({
        "message": "Tous les orders ont été retirés avec succès",
        "count": orders.count(),
    })