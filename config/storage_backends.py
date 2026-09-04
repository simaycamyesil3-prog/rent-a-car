from django.contrib.staticfiles.storage import ManifestStaticFilesStorage

#Django'nun kendi hash'li (cache-busting) statik dosya deposunu kullaniyoruz - bu,
#whitenoise middleware'inin dosyalari dogru bulup sunmasi icin gerekliydi (sadece
#duz/hashsiz depo kullaninca statik dosyalar hic sunulmuyordu). Whitenoise'un KENDI
#deposunu (sikistirma yapan) kullanmiyoruz cunku o, build sirasinda TUM statik
#dosyalari tek tek sikistirmaya calisiyor ve bu Django'nun bu surumunde gercekte var
#olmayan bazi admin/vendor dosyalarinda (icon-debug.svg, select2 dil dosyalari gibi)
#build'i tamamen durduruyordu. Bu haliyle dosyalar sikistirilmadan sunulacak - performans
#acisindan onemsiz bir fark, ama build'i hicbir zaman durdurmaz
class LenientStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            return name
