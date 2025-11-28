import random

from api.models import Deny

def generate_otp():
    return str(random.randint(100000, 999999))

def can_join_church(user, church):
    # Vérifie si l'utilisateur est banni
    if Deny.objects.filter(user=user, church=church).exists():
        return False, "You have been banned from this church."
    return True, ""