from whitenoise.storage import CompressedManifestStaticFilesStorage

#Django admin'in CSS dosyalari bazen (whitenoise'un siki modda aradigi) bir ikon
#dosyasina referans veriyor ama o dosya gercekte toplanmiyor - varsayilan davranista
#bu durum build'i tamamen durduruyor (CommandError). manifest_strict = False ile
#whitenoise bunun icin sadece uyari basip devam ediyor, build durmuyor
class LenientStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False
