from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from api.models import Church,ChurchAdmin,Subscription,User
from api.serializers import ChurchAdminSerializer, OwnerSerializer,SubChurchCreateSerializer,ChurchCreateSerializer, MemberSerializer,SubscriptionSerializer,ChurchSerializer, UserMeSerializer, UserSerializer
from api.permissions import IsAuthenticatedUser, IsSuperAdmin
from rest_framework import status
from django.db.models import Count
from django.db.models import Q
from api.services.notify import create_and_send_whatsapp_notification
from django.utils.text import slugify


@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def create_church_view(request):
    serializer = ChurchCreateSerializer(data=request.data)
    user = request.user
    user.refresh_from_db()
    if serializer.is_valid():
        church = serializer.save(owner=request.user)
        # add owner as ChurchAdmin (OWNER role)
        ChurchAdmin.objects.create(church=church, user=request.user, role="OWNER")
        # create free subscription
        Subscription.objects.create(church=church, plan="FREE", is_active=True)
        create_and_send_whatsapp_notification(
        user=request.user,
        title="Eglise Créée Avec Succès",
        title_eng="Church created successfully",
        message="Votre église a été créée avec succès. Merci de procéder à la certification et de compléter les informations nécessaires afin d’activer l’accès à l’enregistrement et à la publication de contenu.",
        message_eng="Your church has been created successfully! To unlock all features, please verify your church and complete its information. You will then be able to publish content",
        template_name="welcome_message",  # Nom du template WhatsApp que tu as créé sur Meta
        template_params=[]  # Paramètres dynamiques si nécessaire
        )
        if hasattr(user, "current_church"):
            user.current_church = church
            user.save(update_fields=["current_church"])
        return Response(ChurchSerializer(church).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def create_subchurch_view(request, church_id):
    parent_church = get_object_or_404(Church, id=church_id)

    serializer = SubChurchCreateSerializer(data=request.data)
    user = request.user
    user.refresh_from_db()

    if serializer.is_valid():
        # injecter le parent ICI !!!
        church = serializer.save(owner=user, parent=parent_church)

        # add owner as ChurchAdmin (OWNER role)
        ChurchAdmin.objects.create(church=church, user=user, role="OWNER")

        # create free subscription
        Subscription.objects.create(church=church, plan="FREE", is_active=True)

        create_and_send_whatsapp_notification(
            user=user,
            title="Eglise Créée Avec Succès",
            title_eng="Church created successfully",
            message=(
                "Votre église a été créée avec succès. "
                "Merci de procéder à la certification et de compléter les informations nécessaires "
                "afin d’activer l’accès à l’enregistrement et à la publication de contenu."
            ),
            message_eng=(
                "Your church has been created successfully! To unlock all features, "
                "please verify your church and complete its information. "
                "You will then be able to publish content"
            ),
            template_name="welcome_message",
            template_params=[]
        )

        # update current_church
        if hasattr(user, "current_church"):
            user.current_church = church
            user.save(update_fields=["current_church"])

        return Response(ChurchSerializer(church).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_my_churches(request):
    qs = Church.objects.filter(owner=request.user) | Church.objects.filter(admins__user=request.user)
    qs = qs.distinct()
    serializer = ChurchSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsSuperAdmin])
def verify_church_view(request, church_id):
    church = get_object_or_404(Church, id=church_id)
    action = request.data.get("action")
    if action == "APPROVE":
        church.status = "APPROVED"
        church.is_verified = True
        church.activated_at = timezone.now()
        church.save()
        # create notification to owner (in-app + whatsapp)
        from api.services.notify import create_and_send_whatsapp_notification
        create_and_send_whatsapp_notification(church.owner, "Église approuvée", f"Votre église {church.title} a été approuvée.", template_name="church_approved", template_params=[church.title])
        return Response({"status":"ok","message":"approved"})
    elif action == "REJECT":
        church.status = "REJECTED"
        church.is_verified = False
        church.save()
        return Response({"status":"ok","message":"rejected"})
    return Response({"error":"invalid action"}, status=400)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def add_church_admin(request, church_id):
    church = get_object_or_404(Church, id=church_id)
    # only existing church owner or SADMIN can add admins
    if church.owner != request.user and getattr(request.user,"role",None) != "SADMIN":
        return Response({"error":"Not allowed"}, status=403)
    user_id = request.data.get("user_id")
    role = request.data.get("role","ADMIN")
    # get user
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error":"user not found"}, status=404)
    ca, created = ChurchAdmin.objects.get_or_create(church=church, user=user, defaults={"role":role})
    if not created:
        ca.role = role
        ca.save()
    return Response(ChurchAdminSerializer(ca).data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_sub_churches(request, church_id):
    parent = get_object_or_404(Church, id=church_id)
    subs = parent.sub_churches.all()
    serializer = ChurchSerializer(subs, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def list_users(request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(["PUT", "PATCH"])
@permission_classes([IsSuperAdmin])
def update_church(request, church_id):
    church = get_object_or_404(Church, id=church_id)

    serializer = ChurchSerializer(church, data=request.data, partial=True)

    if serializer.is_valid():
        updated = serializer.save()

        # 🔥 Mettre à jour le slug si le titre change
        if "title" in request.data:
            updated.slug = slugify(updated.title)
            updated.save()

        return Response(ChurchSerializer(updated).data)

    return Response(serializer.errors, status=400)

@api_view(["DELETE"])
@permission_classes([IsSuperAdmin])
def delete_church(request, church_id):
    church = get_object_or_404(Church, id=church_id)
    church.delete()
    return Response({"detail": "Church deleted successfully"})

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticatedUser])
def update_self(request):
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_self(request):
    user = request.user
    user.delete()
    return Response({"detail": "Your account has been deleted"})

@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def list_churches(request):
    churches = Church.objects.all()
    serializer = ChurchSerializer(churches, many=True)
    return Response(serializer.data)


# 
@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def list_owners(request):
    owners = User.objects.filter(church_roles__role="OWNER").distinct()
    serializer = OwnerSerializer(owners, many=True)
    return Response(serializer.data)

@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_church_by_owner(request, church_id):
    church = get_object_or_404(Church, id=church_id)

    # Vérification du owner
    if request.user != church.owner:
        return Response(
            {"detail": "You are not allowed to delete this church."},
            status=403
        )

    church.delete()
    return Response({"detail": "Church deleted successfully"})

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticatedUser])
def update_church_by_owner(request, church_id):
    church = get_object_or_404(Church, id=church_id)

    # 🔥 Vérifier que l'utilisateur est OWNER via ChurchAdmin
    is_owner = ChurchAdmin.objects.filter(
        church=church,
        user=request.user,
        role="OWNER"
    ).exists()

    if not is_owner:
        return Response(
            {"detail": "You are not allowed to update this church."},
            status=403
        )

    serializer = ChurchSerializer(church, data=request.data, partial=True)

    if serializer.is_valid():
        updated_church = serializer.save()

        # 🔥 Mettre à jour le slug si le titre change
        if "title" in request.data:
            updated_church.slug = slugify(updated_church.title)
            updated_church.save()

        return Response(ChurchSerializer(updated_church).data)

    return Response(serializer.errors, status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def me(request):
    serializer = UserMeSerializer(request.user)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def churches_metrics(request):
    user = request.user
    if user.role != "SADMIN":
        return Response({"detail": "Unauthorized"}, status=403)

    total_churches = Church.objects.count()
    approved_churches = Church.objects.filter(status="APPROVED").count()
    pending_churches = Church.objects.filter(status="PENDING").count()
    rejected_churches = Church.objects.filter(status="REJECTED").count()

    total_users = User.objects.count()

    members_by_month = (
        User.objects
        .extra(select={'month': "strftime('%%m', created_at)"})
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    top_churches = (
        Church.objects
        .annotate(members=Count("members"))
        .order_by("-members")[:10]
        .values("id", "title", "members")
    )

    return Response({
        "stats": {
            "total_churches": total_churches,
            "approved_churches": approved_churches,
            "pending_churches": pending_churches,
            "rejected_churches": rejected_churches,
            "total_users": total_users,
            "members_by_month": list(members_by_month),
            "top_churches": list(top_churches),
        }
    })

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def get_current_user(request):
    serializer = UserMeSerializer(request.user)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def filter_church_members(request, church_id):
    role = request.GET.get("role")
    commission_id = request.GET.get("commission_id")
    search = request.GET.get("search")

    qs = User.objects.filter(current_church_id=church_id)

    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(phone_number__icontains=search)
        )

    if role:
        qs = qs.filter(
            church_commissions__church_id=church_id,
            church_commissions__role=role
        ).distinct()

    if commission_id:
        qs = qs.filter(
            church_commissions__church_id=church_id,
            church_commissions__commission_id=commission_id
        ).distinct()

    return Response(UserMeSerializer(qs, many=True).data)
