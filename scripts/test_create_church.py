import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'photizon.settings')
import django

django.setup()

from api.models import Church
from api.serializers import ChurchSerializer

try:
    c = Church.objects.create(title='Script Church Test')
    # set phones after creation to use model property
    c.phone_number_1 = '+237600000001'
    c.phone_number_2 = '+237622222222'
    c.save()

    print('Created Church id=', c.id)
    print('phone_numbers() ->', c.phone_numbers())
    print('phone_number (compat) ->', c.phone_number)
    print('Serialized ->')
    print(ChurchSerializer(c).data)
except Exception as e:
    print('ERROR:', e)
    sys.exit(2)
