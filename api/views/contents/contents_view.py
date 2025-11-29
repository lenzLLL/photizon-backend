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
# permissions existantes
from api.permissions import IsAuthenticatedUser
# utilitaires si besoin
from django.utils import timezone


@api_view(["POST"])
@permission_classes([IsSuperAdmin])
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
# @permission_classes([IsAuthenticatedUser])
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
@permission_classes([IsAuthenticatedUser])
def create_content(request,church_id):
    church = get_object_or_404(Church, id=church_id)
    # Only church admins/owner or SADMIN can create for other churches (we assume check)
    if not user_is_church_admin(request.user, church):
        return Response({"detail":"Forbidden"}, status=403)
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

    # Injecte l'ID de l'église dans les données du serializer
    data["church"] = church_id
    serializer = PlaylistSerializer(data=data)
    if serializer.is_valid():
        pl = serializer.save()
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
    # Récupérer les 10 derniers contenus vus par l'utilisateur
    last_views_qs = ContentView.objects.filter(user=request.user,id=church_id).order_by("-viewed_at")[:10]
    last_content_ids = last_views_qs.values_list("content_id", flat=True)

    # Récupérer les tags associés à ces contenus
    tag_ids = ContentTag.objects.filter(content_id__in=last_content_ids).values_list("tag_id", flat=True)

    # Recommander des contenus ayant ces tags mais que l'utilisateur n'a pas encore vus
    qs = (
        Content.objects.filter(contenttag__tag_id__in=tag_ids)
        .exclude(id__in=last_content_ids)
        .distinct()[:20]
    )

    serializer = ContentListSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def feed_for_church(request, church_id):
    # Derniers contenus
    latest = list(
        Content.objects.filter(church_id=church_id)
        .order_by("-created_at")[:30]
    )

    # IDs déjà utilisés
    used_ids = {c.id for c in latest}

    # Trending content (par vues), sans doublons
    trending = list(
        Content.objects.filter(church_id=church_id)
        .exclude(id__in=used_ids)
        .annotate(views=Count("contentview"))
        .order_by("-views")[:10]
    )

    # Combine latest + trending
    items = latest + trending

    # Mélange aléatoire
    random.shuffle(items)

    serializer = ContentListSerializer(items, many=True)
    return Response(serializer.data)

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
