KNOWLEDGE_BASE = [
    {"title": "Ortak klasör erişimi", "content": "Grup üyeliğini, paylaşım ve NTFS izinlerini doğrulayın; kullanıcının oturum belirtecini yenileyin."},
    {"title": "VPN bağlantısı", "content": "İnternet erişimini, VPN ağ geçidini, istemci günlüklerini, kimlik bilgilerini ve sertifika geçerliliğini kontrol edin."},
    {"title": "E-posta teslimi", "content": "Hizmet durumunu, posta kutusu kotasını, ileti izlemeyi, taşıma kurallarını ve spam karantinasını kontrol edin."},
]

SERVICE_STATUS = {
    "file-server": {"status": "çalışıyor", "detail": "Yerel demo verisinde aktif olay bulunmuyor."},
    "vpn": {"status": "performans_düşük", "detail": "Demo verisi: kimlik doğrulama gecikmesi normalden yüksek."},
    "email": {"status": "çalışıyor", "detail": "Yerel demo verisinde aktif olay bulunmuyor."},
}

GUIDES = {
    "access": ["Tam kaynağı ve hata mesajını doğrulayın.", "Kimliği ve grup üyeliğini kontrol edin.", "Paylaşım ve dosya sistemi izinlerini karşılaştırın.", "Kimlik bilgilerini yenileyip tekrar deneyin."],
    "network": ["Kapsamı ve etkilenen kullanıcıları belirleyin.", "IP adresleme ve DNS'i kontrol edin.", "Ağ rotasını ve servis portunu test edin.", "Son ağ değişikliklerini inceleyin."],
    "software": ["Hata ve sürüm bilgisini kaydedin.", "Günlükleri ve bağımlılıkları kontrol edin.", "Minimum girdilerle yeniden üretin.", "Geri alınabilir düzeltmeyi test kapsamında uygulayın."],
}


def search_knowledge_base(query: str) -> dict:
    words = {word.lower() for word in query.split() if len(word) > 2}
    matches = [item for item in KNOWLEDGE_BASE if any(word in (item["title"] + " " + item["content"]).lower() for word in words)]
    return {"query": query, "results": matches[:3]}


def check_service_status(service_name: str) -> dict:
    key = service_name.strip().lower()
    return {"service": key, **SERVICE_STATUS.get(key, {"status": "bilinmiyor", "detail": "Servis yerel demo kataloğunda bulunmuyor."})}


def get_troubleshooting_guide(category: str) -> dict:
    key = category.strip().lower()
    return {"category": key, "steps": GUIDES.get(key, ["Belirtileri ve kapsamı toplayın.", "İlgili günlükleri inceleyin.", "Çözülemezse kanıtlarla eskale edin."])}

