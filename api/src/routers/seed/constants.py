SUPPORTED_LOCALES = {
    "en_US": "English (United States)", "en_GB": "English (United Kingdom)", "es_ES": "Spanish (Spain)", "fr_FR": "French (France)",
    "de_DE": "German (Germany)", "it_IT": "Italian (Italy)", "pt_BR": "Portuguese (Brazil)", "ja_JP": "Japanese (Japan)",
    "ko_KR": "Korean (South Korea)", "zh_CN": "Chinese (Simplified)", "ru_RU": "Russian (Russia)", "ar_SA": "Arabic (Saudi Arabia)", "hi_IN": "Hindi (India)"
}

DATA_GENERATORS = {
    "personal": {"name": "Personal Information", "fields": ["first_name", "last_name", "full_name", "email", "phone_number"]},
    "address": {"name": "Address", "fields": ["street_address", "city", "state", "postal_code", "country"]},
    "company": {"name": "Company", "fields": ["company_name", "company_email", "job_title", "department"]},
    "financial": {"name": "Financial", "fields": ["credit_card", "bank_account", "currency", "amount"]},
    "datetime": {"name": "Date/Time", "fields": ["date", "time", "datetime", "timestamp"]},
    "text": {"name": "Text Content", "fields": ["sentence", "paragraph", "text", "word"]},
    "internet": {"name": "Internet Data", "fields": ["url", "domain", "username", "password", "ipv4", "ipv6"]},
    "numeric": {"name": "Numeric Data", "fields": ["integer", "float", "decimal", "percentage"]}
}
