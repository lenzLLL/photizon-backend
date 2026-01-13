from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q,F, Count
from django.utils.text import slugify
from api.permissions import IsAuthenticatedUser, IsSuperAdmin, user_is_church_admin
from api.serializers import CategorySerializer, CommentSerializer, ContentCreateUpdateSerializer, ContentDetailSerializer, ContentListSerializer, PlaylistItemSerializer, PlaylistSerializer, TagSerializer
# imports communs pour serializers + views
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.db import models
import random
# tes modèles (adaptés à ton projet)
from api.models import (
    ChurchAdmin, Content, Category, Tag, ContentTag, Playlist, PlaylistItem,
    ContentView, ContentLike, Comment, Church, User
)
from api.models import TicketType
from api.serializers import TicketTypeSerializer
# permissions existantes
from api.permissions import IsAuthenticatedUser
# utilitaires si besoin
from django.utils import timezone
from datetime import timedelta
from itertools import zip_longest


@api_view(["POST"])
# @permission_classes([IsSuperAdmin])
def create_category(request):
    data = request.data.copy()
    if "name" in data:
        data["slug"] = slugify(data["name"])

    serializer = CategorySerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
def list_categories(request):
    categories = Category.objects.all().order_by("name")
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def get_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    serializer = CategorySerializer(category)
    return Response(serializer.data)

@api_view(["PUT", "PATCH"])
@permission_classes([IsSuperAdmin])
def update_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    data = request.data.copy()
    if "name" in data:
        data["slug"] = slugify(data["name"])

    serializer = CategorySerializer(category, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    return Response({"detail": "Category deleted successfully"})

class DefaultPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100

# List all content (global or by church) with filters, search, ordering
@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_content(request):
    """
    Query params:
      - church_id
      - type (ARTICLE,AUDIO,EVENT,VIDEO,POST,BOOK)
      - category_id
      - tag (name)
      - search (title/description)
      - ordering (created_at, likes, views) prefixed with - for desc
      - published (true/false)
    """
    qs = Content.objects.all()

    church_id = request.GET.get("church_id")
    ctype = request.GET.get("type")
    category_id = request.GET.get("category_id")
    tag = request.GET.get("tag")
    search = request.GET.get("search")
    published = request.GET.get("published")

    if church_id:
        qs = qs.filter(church_id=church_id)

    if ctype:
        qs = qs.filter(type=ctype)

    if category_id:
        qs = qs.filter(category_id=category_id)

    if tag:
        qs = qs.filter(contenttag__tag__name__icontains=tag)

    if published is not None:
        if published.lower() in ["true","1","yes"]:
            qs = qs.filter(published=True)
        else:
            qs = qs.filter(published=False)

    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    # annotate likes & views for ordering if requested
    qs = qs.annotate(likes_count=Count("contentlike"), views_count=Count("contentview"))

    ordering = request.GET.get("ordering")
    if ordering:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by("-created_at")

    paginator = DefaultPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = ContentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def retrieve_content(request, content_id):
    obj = get_object_or_404(Content, id=content_id)
    serializer = ContentDetailSerializer(obj)
    return Response(serializer.data)


@api_view(["POST"])
# @permission_classes([IsAuthenticatedUser])
def create_content(request,church_id):
    church = get_object_or_404(Church, id=church_id)
    if not getattr(church, "is_verified", False):
        return Response({"detail": "Church not verified"}, status=403)
    # Only church admins/owner or SADMIN can create for other churches (we assume check)
    # if not user_is_church_admin(request.user, church):
    #     return Response({"detail":"Forbidden"}, status=403)
    data = request.data.copy()
    # created_by set to request.user
    data["created_by"] = request.user.id
    data["church"] = church.id
    category_value = request.data.get("category")
    if category_value:
        category = get_object_or_404(Category, id=category_value)
        data["category"] = category.id
    if not data.get("slug"):
        data["slug"] = slugify(data["title"])
    serializer = ContentCreateUpdateSerializer(data=data)
    if serializer.is_valid():
        content = serializer.save()
        # handle tags if provided as comma separated or list
        tags = request.data.get("tags")
        if tags:
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            for t in tags:
                tag_obj, _ = Tag.objects.get_or_create(name=t, defaults={"slug": t.lower().replace(" ","-")})
                ContentTag.objects.get_or_create(content=content, tag=tag_obj)
        return Response(ContentDetailSerializer(content).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["PUT","PATCH"])
@permission_classes([IsAuthenticatedUser])
def update_content(request, content_id):
    obj = get_object_or_404(Content, id=content_id)
    # check permission: creator or church admin or SADMIN (you can implement strict check)
    if request.user != obj.created_by and request.user.role != "SADMIN":
        # also allow church owner/admin check
        if not ChurchAdmin.objects.filter(church=obj.church, user=request.user).exists():
            return Response({"detail":"Forbidden"}, status=403)
    serializer = ContentCreateUpdateSerializer(obj, data=request.data, partial=True)
    if serializer.is_valid():
        content = serializer.save()
        return Response(ContentDetailSerializer(content).data)
    return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_content(request, content_id):
    obj = get_object_or_404(Content, id=content_id)
    if request.user != obj.created_by and request.user.role != "SADMIN":
        if not ChurchAdmin.objects.filter(church=obj.church, user=request.user).exists():
            return Response({"detail":"Forbidden"}, status=403)
    obj.delete()
    return Response({"detail":"deleted"})

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def toggle_like_content(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    like_qs = ContentLike.objects.filter(user=request.user, content=content)
    
    if like_qs.exists():
        # Supprimer le like existant
        like_qs.delete()
        return Response({"liked": False, "note": "like removed"})
    else:
        # Créer un nouveau like
        ContentLike.objects.create(user=request.user, content=content)
        return Response({"liked": True, "note": "like added"})




@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def view_content(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    # Create a new view record on each call so a user can view multiple times (YouTube-like)
    ContentView.objects.create(user=request.user, content=content)
    return Response({"viewed": True})

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_comments(request, content_id):
    qs = Comment.objects.filter(content_id=content_id).order_by("-created_at")
    paginator = DefaultPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = CommentSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def add_comment(request, content_id):
    text = request.data.get("text")
    if not text:
        return Response({"error":"text required"}, status=400)
    content = get_object_or_404(Content, id=content_id)
    c = Comment.objects.create(user=request.user, content=content, text=text)
    return Response(CommentSerializer(c).data, status=201)

@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_comment(request, comment_id):
    c = get_object_or_404(Comment, id=comment_id)
    if c.user != request.user and request.user.role != "SADMIN":
        return Response({"error":"forbidden"}, status=403)
    c.delete()
    return Response({"deleted": True})


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_tags(request):
    qs = Tag.objects.all()
    serializer = TagSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser, IsSuperAdmin])
def create_tag(request):
    name = request.data.get("name")
    if not name:
        return Response({"error":"name required"}, status=400)
    tag, created = Tag.objects.get_or_create(name=name, defaults={"slug": name.lower().replace(" ","-")})
    return Response(TagSerializer(tag).data, status=201 if created else 200)

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticatedUser])
def update_tag(request, tag_id):
    # Vérifie que l'utilisateur est SADMIN
    data = request.data.copy()
    if request.user.role != "SADMIN":
        return Response({"detail": "Forbidden"}, status=403)
    
    tag = get_object_or_404(Tag, id=tag_id)
    if "name" in data:
        data["slug"] = slugify(data["name"])
    serializer = TagSerializer(tag, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_tag(request, tag_id):
    if request.user.role != "SADMIN":
        return Response({"detail": "Forbidden"}, status=403)
    
    tag = get_object_or_404(Tag, id=tag_id)
    tag.delete()
    return Response({"detail": "Tag deleted"}, status=204)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def create_playlist(request):
    data = request.data.copy()
    church_id = request.data.get("church_id")
    if not church_id:
        return Response({"detail": "church_id is required"}, status=400)

    # Ensure church exists and is verified
    church = get_object_or_404(Church, id=church_id)
    if not getattr(church, "is_verified", False):
        return Response({"detail": "Church not verified"}, status=403)

    # Use serializer for validation but pass the actual Church instance on save
    serializer = PlaylistSerializer(data=data)
    if serializer.is_valid():
        pl = serializer.save(church=church)
        return Response(PlaylistSerializer(pl).data, status=201)
    return Response(serializer.errors, status=400)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def add_to_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    content_id = request.data.get("content_id")
    pos = request.data.get("position", 0)

    if not content_id:
        return Response({"detail": "content_id is required"}, status=400)

    content = get_object_or_404(Content, id=content_id)

    # Vérifie si le contenu est déjà dans la playlist
    item, created = PlaylistItem.objects.get_or_create(
        playlist=playlist,
        content=content,
        defaults={"position": pos}
    )

    if not created:
        return Response({"detail": "This content is already in the playlist"}, status=400)

    return Response(PlaylistItemSerializer(item).data, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def reorder_playlist_item(request, item_id):
    # Récupère l'item
    item = get_object_or_404(PlaylistItem, id=item_id)
    playlist = item.playlist

    # Récupère le nouveau rang demandé
    try:
        new_pos = int(request.data.get("position", item.position))
    except (TypeError, ValueError):
        return Response({"detail": "Invalid position"}, status=400)

    # Limite la position dans la plage valide
    playlist_items = list(PlaylistItem.objects.filter(playlist=playlist).order_by("position"))
    max_index = len(playlist_items) - 1
    new_pos = max(0, min(new_pos, max_index))

    # Supprime l'item de sa position actuelle
    playlist_items.remove(item)
    # Insère l'item à la nouvelle position
    playlist_items.insert(new_pos, item)

    # Réattribue les positions pour éviter les doublons
    for index, it in enumerate(playlist_items):
        if it.position != index:
            it.position = index
            it.save(update_fields=["position"])

    return Response(PlaylistItemSerializer(item).data)



@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def trending_content(request, church_id):
    qs = (
        Content.objects.filter(church_id=church_id)
        .annotate(
            likes_count=Count("contentlike", distinct=True),
            views_count=Count("contentview", distinct=True),
        )
        .annotate(
            score=F("views_count") + F("likes_count") * 2
        )
        .order_by("-score")[:20]
    )

    serializer = ContentListSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def recommend_for_user(request,church_id):
    # Récupérer les derniers contenus vus par l'utilisateur dans cette église
    last_views_qs = (
        ContentView.objects
        .filter(user=request.user, content__church_id=church_id)
        .order_by("-viewed_at")[:50]
    )
    last_content_ids = list(last_views_qs.values_list("content_id", flat=True))

    # Si pas de vues récentes, fallback sur trending/latest
    if not last_content_ids:
        qs = (
            Content.objects.filter(church_id=church_id, published=True, is_public=True)
            .annotate(views_count=Count("contentview"), likes_count=Count("contentlike"))
            .order_by("-views_count", "-likes_count")[:20]
        )
        serializer = ContentListSerializer(qs, many=True)
        return Response(serializer.data)

    # Récupérer les tags les plus fréquents dans ces contenus
    tag_counts = (
        ContentTag.objects.filter(content_id__in=last_content_ids)
        .values("tag_id")
        .annotate(freq=Count("id"))
        .order_by("-freq")
    )
    tag_ids = [t["tag_id"] for t in tag_counts]

    # Construire une requête candidate: contenus de la même église, publiés et publics,
    # avec au moins un tag en commun, et que l'utilisateur n'a pas déjà vus
    candidates = (
        Content.objects.filter(church_id=church_id, published=True, is_public=True, contenttag__tag_id__in=tag_ids)
        .exclude(id__in=last_content_ids)
        .annotate(
            tag_matches=Count("contenttag", filter=Q(contenttag__tag_id__in=tag_ids)),
            views_count=Count("contentview", distinct=True),
            likes_count=Count("contentlike", distinct=True),
        )
        .distinct()
    )

    # Score simple: prefer contenus avec plus de matching tags, puis vues, puis likes
    qs = candidates.order_by("-tag_matches", "-views_count", "-likes_count")[:20]
    serializer = ContentListSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def feed_for_church(request, church_id):
    # Respecter uniquement les contenus publiés et publics
    base_qs = Content.objects.filter(church_id=church_id, published=True, is_public=True)

    # Derniers contenus (récent)
    latest = list(base_qs.order_by("-created_at")[:30])

    used_ids = {c.id for c in latest}

    # Trending : vues sur les 7 derniers jours
    threshold = timezone.now() - timedelta(days=7)
    trending = list(
        base_qs
        .exclude(id__in=used_ids)
        .annotate(views_7d=Count("contentview", filter=Q(contentview__viewed_at__gte=threshold)))
        .order_by("-views_7d")[:20]
    )

    # Interleave latest and trending for diversity (keep latest first)
    items = []
    for a, b in zip_longest(latest, trending):
        if a is not None:
            items.append(a)
        if b is not None:
            items.append(b)

    # Paginate the combined list
    paginator = DefaultPagination()
    page = paginator.paginate_queryset(items, request)
    serializer = ContentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def content_stats_global(request):
    total = Content.objects.count()
    by_type = Content.objects.values("type").annotate(total=Count("id")).order_by("-total")
    by_month = Content.objects.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id")).order_by("month")
    top_liked = Content.objects.annotate(likes=Count("contentlike")).order_by("-likes")[:10].values("id","title","likes")
    return Response({
        "total": total,
        "by_type": list(by_type),
        "by_month": list(by_month),
        "top_liked": list(top_liked)
    })


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def content_stats_for_church(request, church_id):
    church = get_object_or_404(Church, id=church_id)
    if not getattr(church, "is_verified", False):
        return Response({"detail": "Church not verified"}, status=403)
    total = Content.objects.filter(church=church).count()
    by_type = Content.objects.filter(church=church).values("type").annotate(total=Count("id")).order_by("-total")
    top_liked = Content.objects.filter(church=church).annotate(likes=Count("contentlike")).order_by("-likes")[:10].values("id","title","likes")
    views = ContentView.objects.filter(content__church=church).count()
    return Response({
        "total": total,
        "by_type": list(by_type),
        "top_liked": list(top_liked),
        "views": views
    })

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_all_playlists(request):
    qs = (
        Playlist.objects
        .select_related("church")
        .prefetch_related(
            "playlistitem_set",
            "playlistitem_set__content",
        )
        .order_by("-created_at")
    )
    church_id = request.GET.get("church_id")
    if church_id:
       qs = qs.filter(church_id=church_id)

    serializer = PlaylistSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def get_playlist_with_items(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    serializer = PlaylistSerializer(playlist)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_ticket_types(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    qs = TicketType.objects.filter(content=content).order_by("name")
    serializer = TicketTypeSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def create_ticket_type(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    # only content creator, church admin/owner or SADMIN can create ticket types
    if request.user != content.created_by and request.user.role != "SADMIN":
        if not ChurchAdmin.objects.filter(church=content.church, user=request.user).exists():
            return Response({"detail": "Forbidden"}, status=403)

    data = request.data.copy()
    data["content"] = content.id
    serializer = TicketTypeSerializer(data=data)
    if serializer.is_valid():
        tt = serializer.save()
        return Response(TicketTypeSerializer(tt).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticatedUser])
def update_ticket_type(request, ticket_type_id):
    tt = get_object_or_404(TicketType, id=ticket_type_id)
    # permission: same as create
    if request.user != tt.content.created_by and request.user.role != "SADMIN":
        if not ChurchAdmin.objects.filter(church=tt.content.church, user=request.user).exists():
            return Response({"detail": "Forbidden"}, status=403)

    serializer = TicketTypeSerializer(tt, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(TicketTypeSerializer(tt).data)
    return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_ticket_type(request, ticket_type_id):
    tt = get_object_or_404(TicketType, id=ticket_type_id)
    if request.user != tt.content.created_by and request.user.role != "SADMIN":
        if not ChurchAdmin.objects.filter(church=tt.content.church, user=request.user).exists():
            return Response({"detail": "Forbidden"}, status=403)
    tt.delete()
    return Response({"detail": "deleted"}, status=204)
