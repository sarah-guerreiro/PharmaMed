import re

# Password pattern
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$"
)

# Email pattern
EMAIL_PATTERN = re.compile(
    r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
)