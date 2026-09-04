
from datetime import date
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Branch, Car, CarModel, Customer, Profile, Reservation

class AvailableCarsConflictTestCase(TestCase):
    def setUp(self):
       
        self.branch = Branch.objects.create(
            name="İstanbul Şubesi",
            city="İstanbul",
            address="Kadıköy/İstanbul",
            location="40.9900, 29.0200"
        )

       
        self.car_model = CarModel.objects.create(
            brand="Toyota",
            model_name="Corolla",
            year=2020,
            transmission="Automatic",
            fuel_type="Gasoline",
            seat_count=5,
            doors=4,
            luggage_capacity=10,
            price_per_day=2000.00,
            segment="sedan",
            body_type="standard"
        )

       
        self.car = Car.objects.create(
            car_model=self.car_model,
            plate="AA 643 G",
            color="Beyaz",
            km=15000,
            status="available",
            current_branch=self.branch
            
        )

        self.customer = Customer.objects.create(
            first_name="Can", 
            last_name="Uyar",
            email="maho1907@gmail.com",
            phone_number="05667356267",
            address="123 Main St",
            identity_number="11111111111",
            license_number="B123456",
        )

        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user, role='staff', branch=self.branch)
        self.client.force_login(self.user)

    
    
    
    #çakışan rezervasyon sorgusu tam içinde kalma 
    def test_available_cars_with_conflicting_reservations(self):
       
        Reservation.objects.create(
            car=self.car,
            customer=self.customer,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 15),
            total_price=500.00,
            status='confirmed',
            pickup_branch=self.branch,
            dropoff_branch=self.branch
        )

        #testin hangi seneryoyu doğruladığı
        response = self.client.get(reverse('available_cars'), {
            'start_date': '2024-01-12',
            'end_date': '2024-01-14'
        })

        #viewın template e ne gönderdiğine doğrudan erişim
        available_cars = response.context['cars'] 
        self.assertNotIn(self.car, available_cars)

    #tamamen kapsama
    def test_fully_encompassing_range_is_not_available(self):
       
        Reservation.objects.create(
            car=self.car,
            customer=self.customer,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 15),
            total_price=500.00,
            status='confirmed',
            pickup_branch=self.branch,
            dropoff_branch=self.branch
        )

        response = self.client.get(reverse('available_cars'), {
                'start_date': '2024-01-08',
                'end_date': '2024-01-18'
        })

        available_cars = response.context['cars'] 
        self.assertNotIn(self.car, available_cars)

     #baştan kısmi çakışma
    def test_partial_overlap_from_start_is_not_available(self):
       
        Reservation.objects.create(
            car=self.car,
            customer=self.customer,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 15),
            total_price=500.00,
            status='confirmed',
            pickup_branch=self.branch,
            dropoff_branch=self.branch
        )

        response = self.client.get(reverse('available_cars'), {
                'start_date': '2024-01-08',
                'end_date': '2024-01-12'
        })

        available_cars = response.context['cars'] 
        self.assertNotIn(self.car, available_cars)


     #sondan kısmi çakışma
    def test_partial_overlap_from_end_is_not_available(self):
       
        Reservation.objects.create(
            car=self.car,
            customer=self.customer,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 15),
            total_price=500.00,
            status='confirmed',
            pickup_branch=self.branch,
            dropoff_branch=self.branch
        )

        response = self.client.get(reverse('available_cars'), {
                'start_date': '2024-01-12',
                'end_date': '2024-01-17'
        })

        available_cars = response.context['cars'] 
        self.assertNotIn(self.car, available_cars)

     #bitişik
    def test_adjacent_range_is_available(self):
       
        Reservation.objects.create(
            car=self.car,
            customer=self.customer,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 15),
            total_price=500.00,
            status='confirmed',
            pickup_branch=self.branch,
            dropoff_branch=self.branch
        )

        response = self.client.get(reverse('available_cars'), {
                'start_date': '2024-01-15',
                'end_date': '2024-01-18'
        })

        available_cars = response.context['cars'] 
        self.assertIn(self.car, available_cars)


     #tamamen ayrık
    def test_completely_separate_range_is_available(self):
       
        Reservation.objects.create(
            car=self.car,
            customer=self.customer,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 15),
            total_price=500.00,
            status='confirmed',
            pickup_branch=self.branch,
            dropoff_branch=self.branch
        )

        response = self.client.get(reverse('available_cars'), {
                'start_date': '2024-01-17',
                'end_date': '2024-01-18'
        })

        available_cars = response.context['cars'] 
        self.assertIn(self.car, available_cars)


class ReservationViewTestCase(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name="İstanbul Şubesi",
            city="İstanbul",
            address="Kadıköy/İstanbul",
            location="40.9900, 29.0200"
        )
        self.car_model = CarModel.objects.create(
            brand="Toyota",
            model_name="Corolla",
            year=2020,
            transmission="Automatic",
            fuel_type="Gasoline",
            seat_count=5,
            doors=4,
            luggage_capacity=10,
            price_per_day=2000.00,
            segment="sedan",
            body_type="standard"
        )
        self.user = User.objects.create_user(username='testuser2', password='testpass')
        self.profile = Profile.objects.create(user=self.user, role='staff', branch=self.branch)
        self.client.force_login(self.user)
    
    def _form_data(self, start_date: str, end_date: str) -> dict[str, str | int]:
        return {
            'start_date': start_date,
            'end_date': end_date,
            'dropoff_branch': self.branch.pk,
            'first_name': 'Ayşe',
            'last_name': 'Yılmaz',
            'email': 'ayse@example.com',
            'phone_number': '05551112233',
            'address': 'Test Adres',
            'identity_number': '22222222222',
            'license_number': 'B999999',
        }
    #müsait olmayan (bakımdaki) araca rezervasyon yapılamaz
    def test_cannot_reserve_car_that_is_not_available(self):
        car = Car.objects.create(
            car_model=self.car_model,
            plate="BB 111 A",
            color="Siyah",
            km=5000,
            status="maintenance",
            current_branch=self.branch,
        )

        response = self.client.post(
            reverse('rezervation', kwargs={'pk': car.pk}),
            self._form_data('2024-02-01', '2024-02-05'),
        )

        self.assertEqual(response.context['error'], 'Bu araç şu anda müsait değil.')
        self.assertEqual(Reservation.objects.count(), 0)
    
    #çakışan tarihli araca rezervasyon yapılamaz
    def test_cannot_reserve_car_with_conflicting_dates(self):
        car = Car.objects.create(
            car_model=self.car_model,
            plate="CC 222 B",
            color="Beyaz",
            km=8000,
            status="available",
            current_branch=self.branch,
        )
        existing_customer = Customer.objects.create(
            first_name="Can",
            last_name="Uyar",
            email="can@example.com",
            phone_number="05667356267",
            address="123 Main St",
            identity_number="11111111111",
            license_number="B123456",
        )
        Reservation.objects.create(
            car=car,
            customer=existing_customer,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 15),
            total_price=500.00,
            status='confirmed',
            pickup_branch=self.branch,
            dropoff_branch=self.branch,
        )

        response = self.client.post(
            reverse('rezervation', kwargs={'pk': car.pk}),
            self._form_data('2024-01-12', '2024-01-14'),
        )

        self.assertEqual(response.context['error'], 'Bu araç seçilen tarihlerde müsait değil.')
        self.assertEqual(Reservation.objects.count(), 1)


