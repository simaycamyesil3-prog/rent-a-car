# Rent A Car - Çok Şubeli Araç Kiralama Sistemi

Bu proje, stajım kapsamında KKTC'de faaliyet gösteren çok şubeli bir araç kiralama şirketi için geliştirdiğim bir Django backend sistemi. Aşağıda projeye ne eklediğimi, hangi kararları neden aldığımı ve yol boyunca çıkan sorunları nasıl çözdüğümü anlatıyorum.

## Proje Ne Yapıyor

Sistem, birden fazla şubesi olan bir kiralama şirketinin günlük operasyonunu yönetiyor: araç envanteri, müşteri rezervasyonu, araç teslimi (checkout), araç iadesi (checkin) ve şubeler arası araç transferi. Kullanıcılar iki role ayrılıyor: **admin** (tüm şubeleri görür, transfer başlatabilir) ve **personel** (sadece kendi şubesini görür).

## Yetkilendirme Nasıl Çalışıyor

Projenin can alıcı noktası, her view'da "bu kullanıcı hangi şubeleri görebilir" kontrolünü tekrar tekrar yazmak yerine bunu `CarManager` ve `BranchManager` adında iki custom manager'a taşımam oldu. `Car.objects.for_user(user)` ve `Branch.objects.for_user(user)` çağrıları, kullanıcının profiline (`Profile.role`) bakıp admin ise her şeyi, değilse sadece kendi şubesini döndürüyor. Bu sayede yetkilendirme mantığı tek bir yerde yaşıyor, her view'da aynı kontrolü kopyala-yapıştır yapmıyorum.

## Rezervasyon Akışı

Müşteri bir araç seçtiğinde (`rezervation` view), sistem önce aracın müsait olup olmadığına, sonra da seçilen tarih aralığının o araç için başka bir rezervasyonla çakışıp çakışmadığına bakıyor (tarih aralığı çakışması `start_date__lt` / `end_date__gt` sorgusuyla kontrol ediliyor). Müşteri aracı aldığı şubeden farklı bir şubeye bırakmak isterse, `ONE_WAY_FEE` adında sabit bir tek yön ücreti fiyata ekleniyor.

## Teslim (Checkout) ve İade (Checkin)

Personel aracı müşteriye teslim ederken (`checkout`) plakayı doğruluyor, çıkış km'sini kaydediyor ve isteğe bağlı olarak araç fotoğrafları yükleyebiliyor (`CarImage` modeli, `request.FILES.getlist('images')` ile). İade sırasında (`checkin`) iade km'si, hasar notu ve iade tarihi kaydediliyor; iade tarihi rezervasyonun bitiş tarihinden sonraysa geç kalınan her gün için ekstra ücret otomatik olarak `total_price`'a ekleniyor. Erken iade durumunda ise kod tarafında bir şey yapılmıyor bilinçli olarak — para iadesi yapılmıyor, aracı müsait hale getirmek elle (admin/personel) yapılıyor.

### Araç İkame Özelliği

Bir müşteri aracını geç iade ederse, o aracın bir sonraki rezervasyonu için checkout yapılmak istendiğinde araç hâlâ "kirada" görünüyor olabilir. Bunun için checkout akışına bir ikame mantığı ekledim: araç müsait değilse, personel aynı şubedeki müsait araçlardan birini seçip rezervasyona atayabiliyor. Burada bilinçli bir tasarım kararı var: `total_price` değişmiyor, çünkü müşteri zaten baştan onayladığı fiyatla anlaşmış durumda, sadece hangi fiziksel aracı kullandığı değişiyor. Bunu test ederken bir ara fiyatın değiştiğini sanıp şüphelenmiştim, ama `Reservation` modelinde fiyatı otomatik değiştirecek herhangi bir `save()` override'ı olmadığını görünce bunun bir hata değil, test verisiyle ilgili bir karışıklık olduğunu anladım.

## Transfer Modülü

Şirket bazen bir müşterinin aracı bir şubeden alıp başka bir şubeye bırakması sonucu (örneğin Ercan'dan alınan araç Girne'de bırakılınca) ya da idari kararla bir aracı başka bir şubeye taşıması gerekiyor. Bunu sadece admin başlatabiliyor. KKTC'de ada bir günde uçtan uca geçilebildiği için, transfer edilen bir araç aynı gün fiziksel olarak yeni şubeye ulaşmış olsa da, ertesi güne kadar tekrar kiralanamıyor — bu bir günlük bekleme süresi iş kuralı olarak `Car.transfer_date` alanıyla takip ediliyor.

Bunu otomatik olarak müsait hale getirecek bir zamanlanmış görev (cron/scheduler) altyapımız olmadığı için, "lazy sync" dediğim bir yöntem kullandım: `CarManager.sync_transfers()` metodu, transfer tarihinden bir gün geçmiş tüm araçları toplu olarak (`update()` ile, tek tek `save()` çağırmadan) tekrar `available` yapıyor, ve bu metod ilgili sayfalar (müsait araç listesi, transfer sayfası) her açıldığında çağrılıyor. Yani sistem "arka planda" değil, "birisi bu sayfaya her baktığında" senkronize oluyor. Her transfer ayrıca `Transfer` modeliyle kim-ne zaman-nereden-nereye bilgisiyle kayıt altına alınıyor, ileride denetim/geçmiş gerekirse diye.

## Arayüz (CSS)

Başta her sayfa kendi `<html><head><body>` yapısını taşıyordu, bu hem tekrarlıydı hem de tutarsızdı. Tüm sayfaları tek bir `base.html` üzerinden `{% extends %}` ile miras alacak şekilde yeniden yapılandırdım; ortak head, navbar ve script'ler tek yerde yaşıyor. Stil için Bootstrap'i temel aldım (form, buton, kart, liste bileşenleri için), üzerine küçük bir `style.css` ile kendi dokunuşlarımı ekledim. Giriş yapan kullanıcı için üstte bir navigasyon menüsü var; Transfer linki sadece admin rolündeki kullanıcılara görünüyor.

## Karşılaştığım ve Çözdüğüm Bazı Sorunlar

- Checkout view'ında ikame formu ile normal teslim formu başta tek bir `<form>` içindeydi; araç müsaitken de ikame `<select>` alanı `required` olduğu için tarayıcı formu hiç göndermiyordu. İki formu birbirini dışlayan `{% if %}/{% else %}` bloklarına ayırarak çözdüm.
- Checkout view'ında "araç müsait değil" kontrolünü GET/POST ayrımından önceye aldım, böylece ikame ekranı hem sayfa ilk açıldığında hem de form tekrar gönderildiğinde aynı şekilde görünüyor.
- Django admin panelinin "Değişiklik geçmişi" özelliğinin sadece admin panelinden yapılan değişiklikleri kaydettiğini, kod içinden yapılan `.save()` çağrılarını göstermediğini fark ettim — bu yüzden şüphelendiğim fiyat sorununu admin geçmişinden değil, doğrudan model kodunu okuyarak çözdüm.
- Dosya yüklemenin çalışması için `<form>` etiketine `enctype="multipart/form-data"` eklemem gerektiğini öğrendim, aksi halde `request.FILES` hep boş geliyordu.

## Bilerek Şimdilik Bırakılan Konular

Şu an bilinçli olarak dokunmadığım birkaç nokta var: `checkin`/`checkout`'taki birden fazla model kaydı (kontrat + araç + rezervasyon) bir `transaction.atomic()` bloğuyla sarılmış değil; rezervasyon formunda bitiş tarihinin başlangıçtan önce olması sunucu tarafında engellenmiyor (şu an sadece JS ile takvimde engelleniyor); ve müsait araçları tarih/şubeye göre filtreleyen `available_cars` view'ı arka planda hazır olsa da bunun için bir form arayüzü henüz yapılmadı. Bunlar bilinen eksikler, ileride ele alınacak.

## Nasıl Çalıştırılır

```
python3 -m venv venv
source venv/bin/activate
pip install django
python3 manage.py migrate
python3 manage.py runserver
```
