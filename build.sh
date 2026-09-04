#!/usr/bin/env bash
# Render bu scripti her deploy'da çalıştırıyor: paketleri kurar, statik dosyaları
# tek bir klasörde toplar, migration'ları uygular ve örnek verileri yükler.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# main/fixtures/sample_data.json içindeki örnek şube/araç/müşteri verisini yüklüyoruz
# (loaddata aynı pk'ya sahip kayıtları güncellediği için tekrar tekrar çalıştırmak güvenli)
python manage.py loaddata main/fixtures/sample_data.json
