from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from api.models import Church, Subscription, User, OTP,Notification
from api.serializers import SubscriptionSerializer, UserSerializer
from api.services.whatsapp import send_otp_whatsapp
from api.permissions import IsAuthenticatedUser, IsSuperAdmin, is_church_admin
from rest_framework.decorators import api_view, permission_classes, authentication_classes

from api.services.notify import create_and_send_whatsapp_notification


@api_view(["POST"])
@authentication_classes([])
def send_otp_view(request):
    phone = request.data.get("phone")

    if not phone:
        return Response({"error": "Le numéro est requis"}, status=400)

    result = send_otp_whatsapp(phone)

    if result.get("status") == "error":
        return Response(result, status=status.HTTP_429_TOO_MANY_REQUESTS)

    return Response({"message": "OTP envoyé"}, status=200)

@api_view(["POST"])
@authentication_classes([])
def verify_otp_view(request):
    phone = request.data.get("phone")
    code = request.data.get("code")

    if not phone or not code:
        return Response({"error": "phone et code obligatoires"}, status=400)

    # 1. Vérification OTP
    try:
        otp_obj = OTP.objects.get(phone=phone, otp=code)
    except OTP.DoesNotExist:
        return Response({"error": "OTP incorrect"}, status=400)

    if otp_obj.is_expired():
        return Response({"error": "OTP expiré"}, status=400)
    

    # 2. Récupérer / créer l'utilisateur
    user, created = User.objects.get_or_create(
        phone_number=phone,
    )
    if created:
        Notification.objects.create(
            user=user,
            title="Bienvenue Sur Photizon",
            eng_title="Welcome To Photizon",
            message="Bienvenue sur Photizon ! Veuillez entrer le code de votre église pour accéder aux contenus de votre communauté et rester connecté avec votre famille d’église..",
            eng_message="Welcome to Photizon! Please enter your church code to access your community’s content and stay connected with your church family.",
            type="SUCCESS"
        )
        create_and_send_whatsapp_notification(
        user=user,
        title_eng="Welcome to Photizon",
        title="Bienvenue sur Photizon",
        message="Bienvenue sur Photizon ! Veuillez entrer le code de votre église pour accéder aux contenus.",
        message_eng="Welcome to Photizon! Please enter your church code to access your community’s content and stay connected with your church family.",
        template_name="welcome_message",  # Nom du template WhatsApp que tu as créé sur Meta
        template_params=[user.phone_number]  # Paramètres dynamiques si nécessaire
        )
    # 3. Générer le token JWT (access + refresh)
    refresh = RefreshToken.for_user(user)

    # 4. Supprimer l'OTP après succès
    otp_obj.delete()

    # 5. Retour
    return Response({
        "success": True,
        "is_new_user": created,
        "user": UserSerializer(user).data,
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    }, status=200)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def get_church_subscription(request, church_id):
    church = get_object_or_404(Church, id=church_id)

    # autorisé : superadmin OU admin/owner de l’église
    if request.user.role != "SADMIN" and not is_church_admin(request.user, church):
        return Response({"detail": "Forbidden"}, status=403)

    sub = getattr(church, "subscription", None)
    if not sub:
        return Response({"detail": "No subscription"}, status=404)
   
    return Response(SubscriptionSerializer(sub).data)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser, IsSuperAdmin])
def create_subscription(request):
    church_id = request.data.get("church_id")
    plan = request.data.get("plan", "FREE")
    expires_at = request.data.get("expires_at")

    church = get_object_or_404(Church, id=church_id)

    if hasattr(church, "subscription"):
        return Response({"detail": "Subscription already exists"}, status=400)

    sub = Subscription.objects.create(
        church=church,
        plan=plan,
        expires_at=expires_at
    )

    return Response(SubscriptionSerializer(sub).data, status=201)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticatedUser])
def update_subscription(request, church_id):
    church = get_object_or_404(Church, id=church_id)

    # Vérifier si la subscription existe ou la créer
    sub, created = Subscription.objects.get_or_create(
        church=church,
        defaults={
            "expires_at": timezone.now() + timedelta(days=30)
        }
    )

    # Si l'utilisateur n'envoie pas expires_at → définir une valeur par défaut
    data = request.data.copy()

    if "expires_at" not in data or not data.get("expires_at"):
        # seulement si c'est une mise à jour partielle
        if not sub.expires_at:
            data["expires_at"] = (timezone.now() + timedelta(days=30)).isoformat()

    serializer = SubscriptionSerializer(sub, data=data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({
            "created": created,      # True = subscription auto-créée
            "subscription": serializer.data
        })

    return Response(serializer.errors, status=400)

@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_subscription(request, church_id):
    church = get_object_or_404(Church, id=church_id)
    sub = getattr(church, "subscription", None)

    if not sub:
        return Response({"detail": "No subscription"}, status=404)

    sub.delete()
    return Response({"detail": "Subscription deleted"})

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def change_subscription_plan(request, church_id):
    plan = request.data.get("plan")
    if plan not in ["FREE", "STARTER", "PRO", "PREMUIM"]:
        return Response({"error": "Invalid plan"}, status=400)

    church = get_object_or_404(Church, id=church_id)
    sub = church.subscription

    # Mettre à jour le plan
    sub.plan = plan

    # Mettre à jour expire_at => maintenant + 1 mois
    sub.expire_at = timezone.now() + timedelta(days=30)

    sub.save()

    return Response({
        "detail": f"Plan updated to {plan}",
        "expire_at": sub.expire_at
    })

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def toggle_subscription_status(request, church_id):
    church = get_object_or_404(Church, id=church_id)
    sub = church.subscription

    sub.is_active = not sub.is_active
    sub.save()

    return Response({"active": sub.is_active})

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def renew_subscription(request, church_id):
    months = int(request.data.get("months", 1))
    church = get_object_or_404(Church, id=church_id)
    sub = church.subscription
 
    # extend expiry date
    if sub.expires_at:
        sub.expires_at += timezone.timedelta(days=30 * months)
    else:
        sub.expires_at = timezone.now() + timezone.timedelta(days=30 * months)
    sub.is_active = True

    sub.save()

    return Response({"detail": "Subscription renewed", "expires_at": sub.expires_at})

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def check_subscription_status(request, church_id):
    church = get_object_or_404(Church, id=church_id)

    if request.user.role != "SADMIN" and not is_church_admin(request.user, church):
        return Response({"detail": "Forbidden"}, status=403)

    sub = church.subscription

    if not sub:
        return Response({"status": "none"})

    now = timezone.now()
    status_value = "active" if sub.is_active and (not sub.expires_at or sub.expires_at > now) else "expired"

    return Response({
        "plan": sub.plan,
        "status": status_value,
        "expires_at": sub.expires_at
    })
@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_subscriptions(request):
    qs = Subscription.objects.select_related("church").order_by("-started_at")
    return Response(SubscriptionSerializer(qs, many=True).data)