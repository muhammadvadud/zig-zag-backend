import os
import django
import random
from decimal import Decimal
from urllib.request import urlopen
from django.core.files.base import ContentFile

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from apps.catalog.models import (
    Category, Color, Style, Room, Material, Tailor, Badge,
    Product, ProductVariant, ProductImage
)
from apps.accounts.models import User

# --- Data Definition ---
CATEGORIES = [
    "Klassik pardalar", "Zamonaviy pardalar", "Blackout pardalar", 
    "Tullar", "Rulon pardalar", "Rim pardalari", "Jalyuzi",
    "Avstriya pardalari", "Fransuz pardalari", "Yapon panellari",
    "Ipli pardalar", "Karnizlar", "Aksessuarlar", "Eksklyuziv", "Eko pardalar"
]

STYLES = [
    "Minimalizm", "Klassika", "Neoklassika", "Loft", 
    "Provans", "Skandinavcha", "Modern", "Eko", "Art Deko"
]

ROOMS = [
    "Zal (Mehmonxona)", "Yotoqxona", "Bolalar xonasi", 
    "Oshxona", "Dahliz", "Ish xonasi (Kabinet)", "Ayvon (Zal)"
]

MATERIALS = [
    "Baxmal (Velvet)", "Atlas", "Zig'ir (Linen)", "Paxta (Cotton)", 
    "Ipak (Silk)", "Jakkard", "Organza", "Vual (Voile)", "Blackout", "Gobelen"
]

COLORS = [
    ("Oq", "#FFFFFF"), ("Qora", "#000000"), ("Kulrang", "#808080"), 
    ("Bej", "#F5F5DC"), ("Oltin", "#FFD700"), ("Ko'k", "#0000FF"), 
    ("Yashil", "#008000"), ("Qizil", "#FF0000"), ("Pushti", "#FFC0CB"), ("Jigarrang", "#A52A2A")
]

TAILORS = [
    ("Malika", "ML", "Klassik va Avstriya pardalari bo'yicha mutaxassis", "4.9"),
    ("Shahnoza", "SH", "Modern va Rim pardalari", "4.8"),
    ("Umid", "UM", "Eksklyuziv o'lchamlar", "4.7"),
]

BADGES = [
    ("Yangi", "#FF5733"), ("Chegirma", "#33FF57"), ("Top sotuv", "#3357FF"), ("Premium", "#FFD700")
]

def slugify(text):
    return text.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "")

print("Kategoriyalar yaratilmoqda...")
cat_objs = []
for i, name in enumerate(CATEGORIES):
    cat_objs.append(Category.objects.create(name=name, slug=slugify(name), sort_order=i))

print("Uslublar, Xonalar, Materiallar yaratilmoqda...")
style_objs = [Style.objects.create(name=s, slug=slugify(s)) for s in STYLES]
room_objs = [Room.objects.create(name=r, slug=slugify(r)) for r in ROOMS]
material_objs = [Material.objects.create(name=m, slug=slugify(m)) for m in MATERIALS]
color_objs = [Color.objects.create(name=c[0], hex=c[1]) for c in COLORS]
tailor_objs = [Tailor.objects.create(name=t[0], initials=t[1], specialty=t[2], rating=Decimal(t[3])) for t in TAILORS]
badge_objs = [Badge.objects.create(name=b[0], color=b[1]) for b in BADGES]

print("Mahsulotlar va ularning rasmlari yaratilmoqda (bu biroz vaqt olishi mumkin, chunki rasmlar yuklab olinadi)...")

adj_list = ["Premium", "Zamonaviy", "Yumshoq", "Klassik", "Eksklyuziv", "Naqshli", "Yorqin", "Sokin"]

def download_image(index):
    try:
        # Use loremflickr to get curtain related images
        url = f"https://loremflickr.com/800/600/curtain?lock={index}"
        response = urlopen(url, timeout=10)
        return ContentFile(response.read(), name=f"curtain_{index}.jpg")
    except Exception as e:
        print(f"Rasm yuklashda xatolik: {e}")
        return None

for i in range(1, 51):
    cat = random.choice(cat_objs)
    mat = random.choice(material_objs)
    room = random.choice(room_objs)
    adj = random.choice(adj_list)
    
    name = f"{adj} {cat.name} - {mat.name} ({i})"
    slug = f"product-{slugify(adj)}-{slugify(cat.name)}-{i}"
    
    prod = Product.objects.create(
        category=cat,
        slug=slug,
        name=name,
        description=f"Bu ajoyib {name} sizning uyingiz ko'rkiga ko'rk qo'shadi. Yuqori sifatli materiallardan tayyorlangan.",
        price_per_m2=Decimal(random.randint(50000, 300000)),
        discount_percent=random.choice([0, 0, 0, 10, 15, 20]),
        is_new=random.choice([True, False]),
        size_mode=Product.SIZE_MODE_BOTH,
        tailor=random.choice(tailor_objs),
        rating_avg=Decimal(random.uniform(4.0, 5.0)).quantize(Decimal("0.1"))
    )
    
    # Add M2M relationships
    prod.materials.add(mat)
    prod.styles.add(random.choice(style_objs))
    prod.rooms.add(room)
    prod.colors.add(random.choice(color_objs))
    
    if random.random() > 0.7:
        prod.badges.add(random.choice(badge_objs))
        
    # Create variants
    for v in range(1, 4):
        ProductVariant.objects.create(
            product=prod,
            name=f"{v*150}x250 sm",
            width_cm=Decimal(v*150),
            height_cm=Decimal("250"),
            price=Decimal(random.randint(200000, 1000000))
        )
        
    # Add an image
    img_file = download_image(i)
    if img_file:
        ProductImage.objects.create(
            product=prod,
            image=img_file,
            is_main=True,
            sort_order=1
        )
    
    print(f"{i}/50: {name} yaratildi.")

print("Superuser yaratilmoqda...")
User = get_user_model()
User.objects.filter(phone="+998901234567").delete()
su = User.objects.create_superuser(phone="+998901234567", password="adminpassword123")
su.full_name = "Asosiy Admin"
su.save()

print("Barcha ma'lumotlar muvaffaqiyatli yaratildi!")
