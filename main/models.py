from django.db import models 
from django.contrib.auth.models import User
from typing import Any
from datetime import date


class CarManager(models.Manager["Car"]):
    def for_user(self, user: User) -> models.QuerySet["Car"]:
        profile = getattr(user, 'profile', None)
        if profile is None:
            return self.none()
        if profile.role == 'admin':
            return self.all()
        return self.filter(current_branch=profile.branch)
    
    def sync_transfers(self) -> None:
        #transfer tarihinden itibaren en az 1 gün geçmiş araçları otomatik olarak tekrar müsait yapıyoruz
        self.filter(
            status='transfer',
            transfer_date__lt=date.today(),
        ).update(status='available')

#dashboarddaki filtreleme mantığını merkez yapıya taşıdık
class BranchManager(models.Manager["Branch"]):
    def for_user(self, user: User) -> models.QuerySet["Branch"]:
        profile = getattr(user, 'profile', None)
        if profile is None:
            return self.none()
        if profile.role == 'admin':
            return self.all()
        return self.filter(pk=profile.branch_id)

class Branch(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    objects: BranchManager = BranchManager()# type: ignore


    def __str__(self):
        
        return self.name

class CarModel(models.Model):

    SEGMENT_CHOICES = [
        ('sedan','Sedan'),
        ('suv','SUV'),
        ('hatchback','Hatchback'),
        ('sport','Sport'),
        ('luxury','Luxury'),
    ]

    BODY_TYPE = [
        ('economic','Economik'),
        ('standard','Standart'),
        ('premium','Premium'),
        ('luxury','Lüks'),
    ]

    brand = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    transmission = models.CharField(max_length=50)
    fuel_type = models.CharField(max_length=50)
    seat_count = models.PositiveIntegerField()
    doors = models.PositiveIntegerField()
    luggage_capacity = models.PositiveIntegerField()
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    segment = models.CharField(choices=SEGMENT_CHOICES, max_length=50)
    body_type = models.CharField(choices=BODY_TYPE, max_length=50)

    def __str__(self):
        return f"{self.brand} {self.model_name} ({self.year})"
    


class Car(models.Model):

    STATUS_CHOICES = [
        ('available','Müsait'),
        ('rented','Kirada'),
        ('maintenance','Bakımda'),
        ('transfer','Transferde'),
    ]
    car_model = models.ForeignKey(CarModel, on_delete=models.PROTECT)
    plate = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=50)
    km = models.PositiveIntegerField()
    status = models.CharField(max_length=50,choices=STATUS_CHOICES,default='available')
    current_branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    transfer_date = models.DateField(null=True, blank=True)

    objects: CarManager = CarManager()  # type: ignore[assignment]

    def __str__(self):
        return f"{self.car_model} - {self.plate}"

class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='car_images/')
    order = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)


    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.is_cover:
            CarImage.objects.filter(car=self.car).update(is_cover=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.car} - {self.order}"
        
class Profile(models.Model):

    ROLE_CHOICES = [
        ('admin','Admin'),
        ('staff','Personel'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
class Customer(models.Model):
    #musteri kendi hesabiyla (self-servis) kayit olup giris yaparsa bu alan doluyor
    #personelin elle olusturdugu (hesabi olmayan/walk-in) musterilerde bos kaliyor
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='customer_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    identity_number = models.CharField(max_length=20, unique=True)
    license_number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending','Beklemede'),
        ('confirmed','Onaylandı'),
        ('active','Aktif'),
        ('cancelled','İptal Edildi'),
        ('completed','Tamamlandı'),
    ]

    car = models.ForeignKey(Car, on_delete=models.PROTECT)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    pickup_branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='pickup_reservations')
    dropoff_branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='dropoff_reservations')

    

    def __str__(self):
        return f"{self.car} - {self.customer} ({self.start_date} to {self.end_date})"
    

class RentalContract(models.Model):

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE)
    delivery_km = models.PositiveIntegerField()
    return_km = models.PositiveIntegerField(null=True, blank=True)
    damage_notes = models.TextField(blank=True)
    delivery_date = models.DateField(auto_now_add=True)
    return_date = models.DateField(null=True, blank=True)
   

    def __str__(self):
        return f"Contract for {self.reservation}"
    
class Transfer(models.Model):
    car = models.ForeignKey(Car, on_delete=models.PROTECT)
    from_branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='transfers_from')
    to_branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='transfers_to')
    transferred_at = models.DateField(auto_now_add=True)
    transferred_by = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.car} - {self.from_branch} -> {self.to_branch} ({self.transferred_at})"

