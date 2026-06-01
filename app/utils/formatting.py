from datetime import datetime

def format_date(value):
    
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")