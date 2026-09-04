from functools import wraps
from typing import Callable, TypeVar, cast
from urllib.parse import urlencode, quote

from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings


from .models import Car, Reservation, Branch, Customer, RentalContract, CarImage, Transfer
from django.db.models import Q, Count

from django.utils import timezone
from datetime import date


#personel/admin mi kontrol ediyoruz (Profile'ı olan herkes personel sayılıyor)
def is_staff_member(user: User) -> bool:
    return getattr(user, 'profile', None) is not None


#next parametresiyle sadece kendi sitemize ait adreslere yönlendiriyoruz (açık yönlendirme riskine karşı)
def _safe_next_url(request: HttpRequest, next_url: str | None) -> str | None:
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return None


#hem giriş yapılmış olmasını hem de personel/admin olmasını istiyoruz
#müşteri hesabıyla giriş yapan biri bu view'lara erişmeye çalışırsa 403 dönüyoruz
#TypeVar ile view fonksiyonunun tipini koruyoruz, aksi halde editör @staff_required
#kullanılan view'ların dönüş tipini "bilinmiyor" olarak görüyor
ViewFunc = TypeVar('ViewFunc', bound=Callable[..., HttpResponse])

def staff_required(view_func: ViewFunc) -> ViewFunc:
    @login_required
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if not is_staff_member(cast(User, request.user)):
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)
    return cast(ViewFunc, wrapper)


# Create your views here.
def index(request: HttpRequest):
    branches = Branch.objects.all()
    return render(request, 'index.html', {'branches': branches})


#anasayfadaki tarih/şube arama formundan geliyor
#giriş yapılmamışsa önce login sayfasına, aranan şey next parametresiyle taşınarak gönderiliyor
def start_search(request: HttpRequest):
    query = urlencode({
        'branch': request.GET.get('branch', ''),
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
    })
    target = f"{reverse('available_cars')}?{query}"

    if request.user.is_authenticated:
        return redirect(target)

    return redirect(f"{reverse('login')}?next={quote(target)}")


#giriş sonrası kullanıcıyı rolüne göre doğru sayfaya yönlendiriyoruz
@login_required
def post_login_redirect(request: HttpRequest):
    if is_staff_member(cast(User, request.user)):
        return redirect('dashboard')
    return redirect('available_cars')


#müşterinin kendi hesabını oluşturduğu public kayıt sayfası
def register(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect('post_login_redirect')

    next_url = _safe_next_url(request, request.POST.get('next') or request.GET.get('next'))

    if request.method == 'GET':
        return render(request, 'registration/register.html', {'next': next_url or ''})

    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip()
    phone_number = request.POST.get('phone_number', '').strip()
    address = request.POST.get('address', '').strip()
    identity_number = request.POST.get('identity_number', '').strip()
    license_number = request.POST.get('license_number', '').strip()
    password = request.POST.get('password', '')
    password2 = request.POST.get('password2', '')

    error = None
    if not all([first_name, last_name, email, identity_number, license_number, password]):
        error = 'Lütfen zorunlu alanları eksiksiz doldurun.'
    elif password != password2:
        error = 'Şifreler birbiriyle uyuşmuyor.'
    elif User.objects.filter(username=email).exists():
        error = 'Bu e-posta ile zaten bir hesap var.'
    elif Customer.objects.filter(email=email).exists():
        error = 'Bu e-posta ile zaten bir müşteri kaydı var. Şubeden oluşturulmuş bir kaydın olabilir, lütfen bizimle iletişime geç.'
    elif Customer.objects.filter(identity_number=identity_number).exists():
        error = 'Bu kimlik numarasıyla zaten bir müşteri kaydı var.'
    elif Customer.objects.filter(license_number=license_number).exists():
        error = 'Bu ehliyet numarasıyla zaten bir müşteri kaydı var.'

    if error:
        return render(request, 'registration/register.html', {'error': error, 'next': next_url or ''})

    #kullanıcı adı olarak e-postayı kullanıyoruz, Django'nun User modelinde username zorunlu
    user = User.objects.create_user(username=email, email=email, password=password)
    Customer.objects.create(
        user=user,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone_number=phone_number,
        address=address,
        identity_number=identity_number,
        license_number=license_number,
    )

    #kayıt olur olmaz otomatik giriş yaptırıyoruz, tekrar login formu doldurtmuyoruz
    auth_login(request, user)

    if next_url:
        return redirect(next_url)
    return redirect('available_cars')


@staff_required
def car_list(request: HttpRequest):
    user = cast(User, request.user)
    car_manager = Car.objects
    
    #select_related kısmı N+1 problemini engellemek ve her araç için ayrı bir sorgu atmamak için 
    cars = car_manager.for_user(user).select_related('car_model')


    return render(
        request,
        'cars/car_list.html',
        {'cars': cars}
    )


@staff_required
def car_detail(request: HttpRequest, pk: int):
    user = cast(User, request.user)
    car_manager = Car.objects

    cars = car_manager.for_user(user)
    car = get_object_or_404(cars, pk=pk)

    return render(
        request,
        'cars/car_details.html',
        {'car': car}
    )


@login_required
def available_cars(request: HttpRequest):
    user = cast(User, request.user)
    car_manager = Car.objects
    is_staff = is_staff_member(user)

    #süresi geçen transferleri güncelliyoruz (zamanlayıcı olmadığı için sayfa her açıldığında senkronize ediyoruz)
    car_manager.sync_transfers()

    branch_id = request.GET.get('branch')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if is_staff:
        branches = Branch.objects.for_user(user)
        cars = car_manager.for_user(user).filter(status='available')
    else:
        #müşteri önce anasayfadaki arama kutusundan şube ve tarih seçmeli
        #bu bilgiler olmadan (ör. linke direkt tıklayarak) sayfaya gelinirse aramayı yaptırmak için anasayfaya geri gönderiyoruz
        if not (branch_id and start_date and end_date):
            return redirect('index')
        #müşteri belirli bir şubeye bağlı değil, tüm şubelerdeki müsait araçları görebilir
        branches = Branch.objects.all()
        cars = car_manager.filter(status='available')
    #bakım ve transferdeki araçları filtreliyor müsait gözükmemesi için 

    #alış şubesi seçimi ekledik
    if branch_id:
        cars = cars.filter(current_branch_id=branch_id)

    if start_date and end_date:

        reserved_car_ids = Reservation.objects.filter(
            status__in=["pending", "confirmed", "active"],
        ).filter(
            Q(start_date__lt=end_date) & Q(end_date__gt=start_date)
        ).values_list('car_id', flat=True)

        cars = cars.exclude(id__in=reserved_car_ids)

    return render(
        request,
        'cars/car_list.html',
        {
            'cars': cars,
            'branches': branches,
            'branch_id': branch_id,
            'start_date': start_date,
            'end_date': end_date,
            'is_staff': is_staff,
        }
    )

@staff_required
def dashboard(request: HttpRequest):
    user = cast(User, request.user)
   
    branches = Branch.objects.for_user(user)
    
    #10 şubeye 10 ayrı veritabanı sorgusu atmamak için annotate kullandık
    #count=sadece bu koşulu sağlayanları say
    branches = branches.annotate(
        total_cars=Count('car'),
        available_cars=Count('car', filter=Q(car__status='available')),
        rented_cars=Count('car',filter=Q(car__status='rented')),
        maintenance_cars=Count('car',filter=Q(car__status='maintenance')),  
        transfer_cars=Count('car',filter=Q(car__status='transfer'))   
    )

    today = timezone.localdate()
    pickups_today = Reservation.objects.filter(
        start_date=today,
        pickup_branch__in=branches,
    ).select_related('customer', 'car', 'pickup_branch')

    returns_today = Reservation.objects.filter(
        end_date=today,
        dropoff_branch__in=branches,
    ).select_related('customer', 'car', 'dropoff_branch')

    return render(
        request,
        'cars/dashboard.html',
        {
            'branches': branches,
            'pickups_today': pickups_today,
            'returns_today': returns_today,
        }
    )

@login_required
def rezervation(request: HttpRequest, pk: int):  
    user = cast(User, request.user)
    car_manager = Car.objects

    #personel kendi şubesindeki/tüm şubelerdeki (admin) araçlara, müşteri tüm müsait araçlara erişebilir
    if is_staff_member(user):
        cars = car_manager.for_user(user)
    else:
        cars = car_manager.all()

    car = get_object_or_404(cars, pk=pk)
    branches = Branch.objects.all()

    #müşteri kendi hesabıyla giriş yaptıysa kendi Customer kaydını kullanıyoruz, bilgileri tekrar girmesine gerek yok
    customer_profile = getattr(user, 'customer_profile', None)

    #araç durumu kontrolü
    if car.status != 'available':
        return render(request, 'cars/reservation_form.html', {'car': car, 'branches': branches, 'customer_profile': customer_profile, 'error': 'Bu araç şu anda müsait değil.'})
    

    #formu göster
    if request.method == 'GET':
        return render(request, 'cars/reservation_form.html', {'car': car, 'branches': branches, 'customer_profile': customer_profile})
    
    #formu doldurup veritabanına gönder
    else:
        start_date = request.POST.get('start_date', '')
        end_date = request.POST.get('end_date', '')

         #tarihleri gerçek data nesnesine çevirir
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

        if not start_date or not end_date:
            return render(request, 'cars/reservation_form.html', {'car': car, 'branches': branches, 'customer_profile': customer_profile, 'error': 'Geçerli bir tarih aralığı giriniz.'})
        
        #bu araç için bu tarih aralığıyla çakışan bir rezervasyon var mı 
        conflicting = Reservation.objects.filter(
            car=car,
            status__in=["pending", "confirmed", "active"],
        ).filter(
            Q(start_date__lt=end_date) & Q(end_date__gt=start_date)
        ).exists()

        if conflicting:
            return render(request, 'cars/reservation_form.html', {'car': car, 'branches': branches, 'customer_profile': customer_profile, 'error': 'Bu araç seçilen tarihlerde müsait değil.'})

        #1.kullanıcı formdan bir şube seçer
        #2.seçilen şube hangisi sorar ve branch nesnesini alır 
        dropoff_branch_id = request.POST.get('dropoff_branch')
        dropoff_branch = get_object_or_404(Branch, pk=dropoff_branch_id)

        if customer_profile is not None:
            #müşteri kendi hesabıyla giriş yaptı, bilgilerini tekrar girmesine gerek yok
            customer = customer_profile
        else:
            #personel walk-in bir müşteri için elle bilgi giriyor
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            address = request.POST.get('address')
            identity_number = request.POST.get('identity_number')
            license_number = request.POST.get('license_number')

            if not first_name or not last_name or not email or not phone_number or not address or not identity_number or not license_number:
                return render(request, 'cars/reservation_form.html', {'car': car, 'branches': branches, 'customer_profile': customer_profile, 'error': 'Lütfen tüm müşteri bilgilerini eksiksiz doldurun.'})
            
            #okuduğumuz değişkenleri kullanarak müşteri kaydı oluşturma 
            customer = Customer.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            address=address,
            identity_number=identity_number,
            license_number=license_number,
            )

        days = (end_date - start_date).days   #iki tarih arasındaki gün farkı
        price = car.car_model.price_per_day * days    #günlük ücret x gün sayısı
        if dropoff_branch != car.current_branch:    #bırakılan şube mevcut şubeden farklıysa
            price += settings.ONE_WAY_FEE    #sabit tek yön ücreti


        Reservation.objects.create(
        car=car,
        customer=customer,
        start_date=start_date,
        end_date=end_date,
        total_price=price,
        pickup_branch=car.current_branch,
        dropoff_branch=dropoff_branch,
        status='pending',
        )

        #müşteri kendi rezervasyonunu yaptıysa kendi rezervasyon listesine, personel yaptıysa araç detayına dönüyor
        if customer_profile is not None:
            return redirect('my_reservations')
        return redirect('car_details', pk=car.pk)


#müşterinin kendi rezervasyonlarını görebildiği sayfa
@login_required
def my_reservations(request: HttpRequest):
    user = cast(User, request.user)
    customer_profile = getattr(user, 'customer_profile', None)

    if customer_profile is None:
        return HttpResponseForbidden()

    reservations = Reservation.objects.filter(
        customer=customer_profile,
    ).select_related('car', 'car__car_model', 'pickup_branch', 'dropoff_branch')

    return render(request, 'cars/my_reservations.html', {'reservations': reservations})


#müşteri kendi rezervasyonunu iptal edebiliyor, ama sadece araç henüz teslim edilmemişse
@login_required
def cancel_reservation(request: HttpRequest, pk: int):
    user = cast(User, request.user)
    customer_profile = getattr(user, 'customer_profile', None)

    if customer_profile is None:
        return HttpResponseForbidden()

    #müşteri sadece kendi rezervasyonunu iptal edebilir, başkasının pk'sini denerse 404 döner
    reservation = get_object_or_404(Reservation, pk=pk, customer=customer_profile)

    #araç zaten teslim edilmişse (rentalcontract varsa) ya da rezervasyon zaten iptal/tamamlanmışsa iptal edilemez
    can_cancel = reservation.status in ('pending', 'confirmed') and not hasattr(reservation, 'rentalcontract')

    if request.method == 'POST' and can_cancel:
        reservation.status = 'cancelled'
        reservation.save()
        #araç bu rezervasyon yüzünden 'transfer' ya da başka bir durumda değilse ekstra bir şey yapmaya gerek yok,
        #çünkü müsaitlik zaten aktif rezervasyonlara bakılarak (available_cars, rezervation) hesaplanıyor

    return redirect('my_reservations')


@staff_required
def checkout(request: HttpRequest, pk: int):
    user = cast(User, request.user)
    branches = Branch.objects.for_user(user)

    #kullanıcının erişebildiği şubelerden çıkan rezervasyonlar arasından istenen pk aranıyor
    #başka şubeden rezervasyon istenirse 404 dönüyor
    reservation = get_object_or_404(
        Reservation.objects.select_related('car', 'customer'),
        pk=pk,
        pickup_branch__in=branches,
    )
    #bu rezervasyon daha önce teslim edilmiş mi kontrolü
    if hasattr(reservation, 'rentalcontract'):
        return render(request, 'cars/checkout_form.html', {'reservation': reservation, 'error': 'Bu rezervasyon zaten teslim edilmiş.'})

    #araç şu an müsait değilse (başka bir kiralamada), teslim işlemi yapılamaz
    if reservation.car.status != 'available':
       
        #personel ikame formundan bir araç seçip gönderdiyse
        if request.method == 'POST' and request.POST.get('substitute_car'):
            substitute_car = get_object_or_404(
                Car.objects.filter(current_branch=reservation.pickup_branch, status='available'),
                pk=request.POST.get('substitute_car'),
            )
            #rezervasyonun aracını ikame araçla değiştiriyoruz, fiyata dokunmuyoruz
            reservation.car = substitute_car
            reservation.save()
            return redirect('checkout', pk=reservation.pk)

        #henüz seçim yapılmadıysa, aynı şubedeki müsait araçları listeleyip ikame formunu gösteriyoruz
        alternative_cars = Car.objects.filter(
            current_branch=reservation.pickup_branch,
            status='available',
        )
        return render(request, 'cars/checkout_form.html', {
            'reservation': reservation,
            'error': 'Bu araç şu anda müsait değil, önce mevcut kiralamanın iadesi yapılmalı.',
            'alternative_cars': alternative_cars,
        })
    
    #formu gösteriyor
    if request.method == 'GET':
        return render(request, 'cars/checkout_form.html', {'reservation': reservation})

    else:
        
        delivery_km = request.POST.get('delivery_km')
        plate = request.POST.get('plate')

        #staff'ın girdiği plaka, rezervasyondaki araçla eşleşiyor mu
        if plate != reservation.car.plate:
            return render(request, 'cars/checkout_form.html', {'reservation': reservation, 'error': 'Girilen plaka rezervasyondaki araçla eşleşmiyor.'})

        #yeni kontrat kaydı oluşturuluyor
        RentalContract.objects.create(
            reservation=reservation,
            delivery_km=delivery_km,
        )


        #staff'ın yüklediği araç görselleri kaydediliyor (opsiyonel)
        images = request.FILES.getlist('images')
        for image in images:
            CarImage.objects.create(car=reservation.car, image=image)

        #araç artık kirada
        reservation.car.status = 'rented'
        reservation.car.save()

        #rezervasyon artık aktif bir kiralama
        reservation.status = 'active'
        reservation.save()

        return redirect('car_details', pk=reservation.car.pk)


@staff_required
def checkin(request: HttpRequest, pk: int):
    user = cast(User, request.user)
    branches = Branch.objects.for_user(user)

    #kullanıcı sadece kendi şubesinden çıkan rezervasyonu iade edebilir
    reservation = get_object_or_404(
        Reservation.objects.select_related('car', 'customer'),
        pk=pk,
        pickup_branch__in=branches,
    )

    #bu rezervasyon hiç teslim edilmemişse (kontrat yoksa) iade yapılamaz
    if not hasattr(reservation, 'rentalcontract'):
        return render(request, 'cars/checkin_form.html', {'reservation': reservation, 'error': 'Bu rezervasyon henüz teslim edilmemiş.'})

    contract: RentalContract = reservation.rentalcontract  # type: ignore[attr-defined]

    #bu rezervasyon zaten iade edilmişse (return_date doluysa) tekrar iade edilemez
    if contract.return_date:  # type: ignore[reportUnknownMemberType]
        return render(request, 'cars/checkin_form.html', {'reservation': reservation, 'error': 'Bu rezervasyon zaten iade edilmiş.'})

    #formu göster
    if request.method == 'GET':
        return render(request, 'cars/checkin_form.html', {'reservation': reservation})

    #formu doldurup gönder
    else:
        return_km_raw = request.POST.get('return_km')
        damage_notes = request.POST.get('damage_notes', '')

        #tarihi gerçek date nesnesine çevirir
        return_date = parse_date(request.POST.get('return_date', ''))

        if not return_date:
            return render(request, 'cars/checkin_form.html', {'reservation': reservation, 'error': 'Geçerli bir iade tarihi giriniz.'})

        if not return_km_raw:
            return render(request, 'cars/checkin_form.html', {'reservation': reservation, 'error': 'Geçerli bir iade km giriniz.'})

        #string olarak gelen km'yi sayıya çeviriyoruz
        return_km = int(return_km_raw)

        #kontrata iade bilgilerini işliyoruz
        contract.return_km = return_km
        contract.damage_notes = damage_notes
        contract.return_date = return_date
        contract.save()  # type: ignore[reportUnknownMemberType]
 
        #geç iade edilirse ekstra gün ücreti ekleniyor, erken iadede fark düşülmüyor
        if return_date > reservation.end_date:
            extra_days = (return_date - reservation.end_date).days
            reservation.total_price += reservation.car.car_model.price_per_day * extra_days
            reservation.save()

        #araç artık müsait ve fiziksel olarak bırakıldığı şubede
        reservation.car.status = 'available'
        reservation.car.current_branch = reservation.dropoff_branch
        reservation.car.save()

        #rezervasyon süreci tamamen bitti
        reservation.status = 'completed'
        reservation.save()

        return redirect('car_details', pk=reservation.car.pk)


@staff_required
def branch_reservations(request: HttpRequest):
    user = cast(User, request.user)
    branches = Branch.objects.for_user(user)

    #kullanıcının erişebildiği şubelerden çıkan tüm rezervasyonlar (tarih filtresi yok, dashboard'dan farklı olarak)
    reservations = Reservation.objects.filter(
        pickup_branch__in=branches,
    ).select_related('customer', 'car', 'pickup_branch', 'dropoff_branch')

    return render(request, 'cars/reservation_list.html', {'reservations': reservations})

@staff_required
def transfer_car(request: HttpRequest):
    user = cast(User, request.user)
    profile = getattr(user, 'profile', None)

    #sadece admin transfer başlatabilir, değilse 403 dönüyoruz
    if profile is None or profile.role != 'admin':
        return HttpResponseForbidden()

    #süresi geçen transferleri güncelliyoruz (zamanlayıcı olmadığı için sayfa her açıldığında senkronize ediyoruz)
    Car.objects.sync_transfers()

    #formu gösteriyor
    if request.method == 'GET':
        cars = Car.objects.filter(status='available')
        branches = Branch.objects.all()
        return render(request, 'cars/transfer_form.html', {'cars': cars, 'branches': branches})

    #formu doldurup gönder
    else:
        car = get_object_or_404(Car, pk=request.POST.get('car'), status='available')
        to_branch = get_object_or_404(Branch, pk=request.POST.get('to_branch'))

        #araç zaten o şubedeyse transfer anlamsız
        if to_branch == car.current_branch:
            cars = Car.objects.filter(status='available')
            branches = Branch.objects.all()
            return render(request, 'cars/transfer_form.html', {'cars': cars, 'branches': branches, 'error': 'Araç zaten bu şubede.'})

        #transfer kaydı oluşturuluyor (kim, ne zaman, nereden nereye - denetim/geçmiş için)
        Transfer.objects.create(
            car=car,
            from_branch=car.current_branch,
            to_branch=to_branch,
            transferred_by=user,
        )

        #araç fiziksel olarak aynı gün yeni şubeye varıyor ama ertesi güne kadar kiralanamıyor
        car.current_branch = to_branch
        car.status = 'transfer'
        car.transfer_date = date.today()
        car.save()

        return redirect('transfer_car')
