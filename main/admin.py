from django.contrib import admin
from .models import Branch
from .models import CarModel
from .models import Car
from .models import CarImage
from .models import Profile
from .models import Customer
from .models import Reservation
from .models import RentalContract
from .models import Transfer

# Register your models here.


admin.site.register(Branch)
admin.site.register(CarModel)
admin.site.register(Car)
admin.site.register(CarImage)
admin.site.register(Profile)
admin.site.register(Customer)
admin.site.register(Reservation)
admin.site.register(RentalContract)
admin.site.register(Transfer)

