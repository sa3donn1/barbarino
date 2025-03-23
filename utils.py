import re
from datetime import datetime

def validate_phone(phone):
    """
    التحقق من أن رقم الهاتف يحتوي على 10 أرقام ويبدأ بـ 1
    مثال: 1234567890
    """
    return bool(re.match(r"^1[0-9]{9}$", phone))

def validate_date(date_str):
    """
    التحقق من صحة التاريخ بصيغة dd/mm/yyyy.
    ثم تحويله إلى صيغة YYYY-MM-DD.
    """
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None

