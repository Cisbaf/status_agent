from datetime import datetime, timezone
import pytz

def convert_time(dt: datetime):
    return dt.astimezone(timezone.utc).astimezone(pytz.timezone('America/Sao_Paulo'))
    