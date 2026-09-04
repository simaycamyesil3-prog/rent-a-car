from whitenoise.storage import CompressedManifestStaticFilesStorage

#Django admin'in CSS dosyasi, kullanilan Django surumunde gercekte var olmayan bir
#simge dosyasina referans veriyor (icon-debug.svg). manifest_strict = False, sadece
#"dosya var ama tabloda kayitli degil" durumunu cozuyor - burada dosyanin kendisi
#hic yok, o yuzden hashed_name'i de eziyoruz: dosya bulunamazsa build'i patlatmak
#yerine (ValueError) referansi oldugu gibi birakip devam ediyoruz. Sonucta sadece
#o tek ikon linki calismaz, sitenin geri kalani ve admin paneli normal calisir
class LenientStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            return name
