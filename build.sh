#!/usr/bin/env bash
# Render bu scripti her deploy'da çalıştırıyor: paketleri kurar, statik dosyaları
# tek bir klasörde toplar, migration'ları uygular ve örnek verileri yükler.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

#Render'in ucretsiz plani diskte hicbir seyi kalici tutmuyor: her deploy'da
#veritabani sifirdan olusuyor, bu yuzden admin (superuser) hesabi da her
#deploy'da yeniden olusturulmali. Kullanici adi/sifre Render'daki ortam
#degiskenlerinden (DJANGO_SUPERUSER_*) okunuyor, kod icinde sifre yazmiyoruz.
#Bu degiskenler tanimli degilse (yerel gelistirmede) bu blok hicbir sey yapmiyor
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi

# main/fixtures/sample_data.json içindeki örnek şube/araç/müşteri verisini yüklüyoruz
# (loaddata aynı pk'ya sahip kayıtları güncellediği için tekrar tekrar çalıştırmak güvenli)
python manage.py loaddata main/fixtures/sample_data.json
