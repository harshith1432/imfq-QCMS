import re
import html
from datetime import datetime, date

class ValidationError(Exception):
    """Custom exception raised when payload validation fails."""
    def __init__(self, message, field=None, error_code="INVALID_INPUT"):
        super().__init__(message)
        self.message = message
        self.field = field
        self.error_code = error_code

# ─────────────────────────────────────────────────────────────────────────────
# SANITIZATION UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def strip_control_characters(val: str) -> str:
    """Removes non-printable control characters and null bytes from a string."""
    if not isinstance(val, str):
        return val
    # Remove null bytes and non-printable control characters (except newline, tab, carriage return)
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', val)

def sanitize_string(val: str, allow_html: bool = False) -> str:
    """Trims whitespace, strips control chars, collapses multi-spaces, and optionally escapes HTML."""
    if not isinstance(val, str):
        return val
    val = strip_control_characters(val).strip()
    if not allow_html:
        # Escape potential script tags and HTML injection vectors
        val = html.escape(val)
    # Collapse multiple consecutive spaces while keeping formatting clean
    val = re.sub(r' {2,}', ' ', val)
    return val

def sanitize_payload(data):
    """Recursively sanitizes strings inside dictionaries, lists, or primitive types."""
    if isinstance(data, str):
        return sanitize_string(data)
    elif isinstance(data, dict):
        return {k: sanitize_payload(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_payload(item) for item in data]
    return data

def prevent_path_traversal(filename: str) -> str:
    """Strips path traversal sequences like ../ or ..\\ from filenames."""
    if not filename:
        return ""
    filename = sanitize_string(filename)
    return re.sub(r'(\.\.[/\\])+', '', filename)

# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def validate_string_length(val: str, field_name: str, min_len: int = 0, max_len: int = 255, required: bool = True):
    """Validates string length and presence."""
    if val is None or (isinstance(val, str) and not val.strip()):
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    
    cleaned = sanitize_string(str(val))
    if len(cleaned) < min_len:
        raise ValidationError(f"{field_name} must be at least {min_len} characters long.", field=field_name)
    if len(cleaned) > max_len:
        raise ValidationError(f"{field_name} cannot exceed {max_len} characters.", field=field_name)
    return cleaned

def validate_email(email: str, field_name: str = "Email address", required: bool = True) -> str:
    """Validates email format and structure."""
    if not email or not str(email).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    
    cleaned = str(email).strip().lower()
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, cleaned) or len(cleaned) > 255:
        raise ValidationError(f"Please provide a valid {field_name.lower()}.", field=field_name)
    return cleaned

def validate_phone(phone: str, field_name: str = "Phone number", required: bool = False) -> str:
    """Validates phone number format."""
    if not phone or not str(phone).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    
    cleaned = str(phone).strip()
    phone_regex = r'^\+?[0-9\s\-()]{7,20}$'
    if not re.match(phone_regex, cleaned):
        raise ValidationError(f"{field_name} format is invalid. Allowed: digits, spaces, hyphens, and optional country code (+) prefix.", field=field_name)
    return cleaned

def validate_password(password: str, field_name: str = "Password") -> str:
    """Validates password complexity (8-128 chars, upper, lower, number, special char)."""
    if not password:
        raise ValidationError(f"{field_name} is required.", field=field_name)
    if len(password) < 8:
        raise ValidationError(f"{field_name} must be at least 8 characters long.", field=field_name)
    if len(password) > 128:
        raise ValidationError(f"{field_name} cannot exceed 128 characters.", field=field_name)
    if not re.search(r'[A-Z]', password):
        raise ValidationError(f"{field_name} must contain at least one uppercase letter (A-Z).", field=field_name)
    if not re.search(r'[a-z]', password):
        raise ValidationError(f"{field_name} must contain at least one lowercase letter (a-z).", field=field_name)
    if not re.search(r'[0-9]', password):
        raise ValidationError(f"{field_name} must contain at least one number (0-9).", field=field_name)
    if not re.search(r'[^A-Za-z0-9]', password):
        raise ValidationError(f"{field_name} must contain at least one special character (!@#$...).", field=field_name)
    return password

def validate_number(val, field_name: str, min_val: float = None, max_val: float = None, required: bool = True):
    """Validates numeric input within min and max boundaries."""
    if val is None or val == "":
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return None
    try:
        num = float(val) if '.' in str(val) else int(val)
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid number.", field=field_name)
        
    if min_val is not None and num < min_val:
        raise ValidationError(f"{field_name} cannot be less than {min_val}.", field=field_name)
    if max_val is not None and num > max_val:
        raise ValidationError(f"{field_name} cannot exceed {max_val}.", field=field_name)
    return num

def validate_enum(val: str, allowed_values: list, field_name: str, required: bool = True) -> str:
    """Validates that a field value is among a predefined set of allowed choices."""
    if not val:
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    cleaned = str(val).strip()
    if cleaned not in allowed_values:
        raise ValidationError(f"Invalid {field_name.lower()}. Allowed options: {', '.join(map(str, allowed_values))}.", field=field_name)
    return cleaned

def validate_date_range(start_date, end_date, start_field="Start date", end_field="End date"):
    """Validates that start date is on or before end date."""
    if start_date and end_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        if start_date > end_date:
            raise ValidationError(f"{start_field} cannot be later than {end_field}.", field=start_field)

def validate_file_upload(file_obj, allowed_extensions: set, max_bytes: int = 10485760):
    """Validates uploaded file size and extension."""
    if not file_obj or not file_obj.filename:
        raise ValidationError("No file selected for upload.", field="file")
    
    filename = prevent_path_traversal(file_obj.filename)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext not in allowed_extensions:
        raise ValidationError(f"File extension '.{ext}' is not permitted. Allowed extensions: {', '.join(sorted(allowed_extensions))}.", field="file")
    
    # Check size
    file_obj.seek(0, 2)
    file_size = file_obj.tell()
    file_obj.seek(0)
    
    if file_size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        raise ValidationError(f"File size exceeds maximum limit of {max_mb:.1f} MB.", field="file")
    
    return filename

# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE BUSINESS & TAX IDENTIFIER VERIFICATION ALGORITHMS
# ─────────────────────────────────────────────────────────────────────────────

def validate_pan(pan: str, field_name: str = "PAN Number", required: bool = False) -> str:
    """Validates Indian Permanent Account Number (PAN) format and entity type code."""
    if not pan or not str(pan).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    
    cleaned = str(pan).strip().upper()
    pan_regex = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    if not re.match(pan_regex, cleaned):
        raise ValidationError(f"Invalid {field_name}. Format must be 5 letters, 4 digits, and 1 letter (e.g. ABCDE1234F).", field=field_name)
    
    entity_code = cleaned[3]
    valid_entities = {'C', 'P', 'H', 'F', 'A', 'T', 'B', 'L', 'J', 'G'}
    if entity_code not in valid_entities:
        raise ValidationError(f"Invalid entity type designation '{entity_code}' in {field_name}.", field=field_name)
        
    return cleaned

def validate_gstin(gstin: str, field_name: str = "GST Number", required: bool = False) -> str:
    """Validates Indian Goods and Services Tax Identification Number (GSTIN) structure and Modulus 36 Checksum."""
    if not gstin or not str(gstin).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    
    cleaned = str(gstin).strip().upper()
    gst_regex = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    if not re.match(gst_regex, cleaned):
        raise ValidationError(f"Invalid {field_name} format. Expected 15-character GSTIN (e.g. 27AAAAA0000A1Z5).", field=field_name)
    
    # State Code check (01 to 38, 97, 99)
    state_code = cleaned[:2]
    valid_states = {f"{i:02d}" for i in range(1, 39)} | {'97', '99'}
    if state_code not in valid_states:
        raise ValidationError(f"Invalid state code '{state_code}' in {field_name}.", field=field_name)
        
    # Validate embedded PAN portion
    pan_part = cleaned[2:12]
    validate_pan(pan_part, field_name=f"{field_name} (PAN portion)", required=True)
    
    # Modulus 36 Checksum Verification
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    char_map = {c: i for i, c in enumerate(chars)}
    
    factor = 1
    total_sum = 0
    mod = len(chars)
    
    for i in range(14):
        code_point = char_map[cleaned[i]]
        digit = code_point * factor
        factor = 2 if factor == 1 else 1
        total_sum += (digit // mod) + (digit % mod)
        
    calc_check_digit = (mod - (total_sum % mod)) % mod
    expected_check_char = chars[calc_check_digit]
    
    if cleaned[14] != expected_check_char:
        raise ValidationError(f"{field_name} checksum validation failed. Invalid checksum character.", field=field_name)
        
    return cleaned

def validate_tan(tan: str, field_name: str = "TAN Number", required: bool = False) -> str:
    """Validates Tax Deduction and Collection Account Number (TAN) format."""
    if not tan or not str(tan).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    cleaned = str(tan).strip().upper()
    tan_regex = r'^[A-Z]{4}[0-9]{5}[A-Z]{1}$'
    if not re.match(tan_regex, cleaned):
        raise ValidationError(f"Invalid {field_name}. Must be 4 letters, 5 digits, and 1 letter (e.g. ABCD12345E).", field=field_name)
    return cleaned

def validate_cin(cin: str, field_name: str = "CIN Number", required: bool = False) -> str:
    """Validates Corporate Identification Number (CIN) format (21 chars)."""
    if not cin or not str(cin).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    cleaned = str(cin).strip().upper()
    cin_regex = r'^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$'
    if not re.match(cin_regex, cleaned) or len(cleaned) != 21:
        raise ValidationError(f"Invalid {field_name}. Must be a valid 21-character CIN (e.g. L12345MH2020PLC123456).", field=field_name)
    return cleaned

def validate_ifsc(ifsc: str, field_name: str = "IFSC Code", required: bool = False) -> str:
    """Validates Indian Financial System Code (IFSC) format."""
    if not ifsc or not str(ifsc).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    cleaned = str(ifsc).strip().upper()
    ifsc_regex = r'^[A-Z]{4}0[A-Z0-9]{6}$'
    if not re.match(ifsc_regex, cleaned):
        raise ValidationError(f"Invalid {field_name}. Format: 4 letters, '0', and 6 digits/letters (e.g. SBIN0001234).", field=field_name)
    return cleaned

def validate_swift(swift: str, field_name: str = "SWIFT/BIC Code", required: bool = False) -> str:
    """Validates SWIFT / BIC code format (8 or 11 characters)."""
    if not swift or not str(swift).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    cleaned = str(swift).strip().upper()
    swift_regex = r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$'
    if not re.match(swift_regex, cleaned):
        raise ValidationError(f"Invalid {field_name}. Must be 8 or 11 alphanumeric characters.", field=field_name)
    return cleaned

def validate_pincode(pincode: str, field_name: str = "PIN Code", required: bool = False) -> str:
    """Validates 6-digit Indian PIN Code format."""
    if not pincode or not str(pincode).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    cleaned = str(pincode).strip()
    pin_regex = r'^[1-9][0-9]{5}$'
    if not re.match(pin_regex, cleaned):
        raise ValidationError(f"Invalid {field_name}. Must be a 6-digit postal code.", field=field_name)
    return cleaned

# Verhoeff algorithm multiplication table
_verhoeff_d = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

# Verhoeff algorithm permutation table
_verhoeff_p = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

def validate_aadhaar(aadhaar: str, field_name: str = "Aadhaar Number", required: bool = False) -> str:
    """Validates 12-digit Indian Aadhaar number using the Verhoeff Checksum Algorithm."""
    if not aadhaar or not str(aadhaar).strip():
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
        
    cleaned = re.sub(r'[\s\-]', '', str(aadhaar).strip())
    if not re.match(r'^[2-9][0-9]{11}$', cleaned):
        raise ValidationError(f"Invalid {field_name}. Must be a 12-digit number starting with 2-9.", field=field_name)
        
    # Verhoeff Checksum calculation
    c = 0
    inverted_digits = [int(d) for d in reversed(cleaned)]
    for i, d in enumerate(inverted_digits):
        c = _verhoeff_d[c][_verhoeff_p[i % 8][d]]
        
    if c != 0:
        raise ValidationError(f"{field_name} checksum validation failed. Invalid number.", field=field_name)
        
    return cleaned

