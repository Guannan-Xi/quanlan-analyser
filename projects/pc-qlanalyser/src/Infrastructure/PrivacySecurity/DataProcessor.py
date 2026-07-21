

def mask_ip_address(ip_address):
    parts = ip_address.split('.')
    if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
        # Masking the last part of the IP address
        masked_ip = '.'.join(parts[:-1]) + '.*'
        return masked_ip
    else:
        return "--.--.--.--"

def mask_string(str):
    if len(str) <= 2:
        return str  # 对于非常短的主机名，不进行脱敏处理
    elif len(str) <= 4:
        return str[:1] + '*' * (len(str) - 1)  # 保留第一个字符，其余替换为*
    else:
        return str[:2] + '*' * (len(str) - 4) + str[-2:]  # 保留首尾各两个字符