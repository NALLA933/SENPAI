"""
Common utilities shared across all modules.
This file contains all shared constants and functions to avoid code duplication.
"""

# ============ RARITY CONFIGURATION ============
RARITY_MAP = {
    1: "⚪ ᴄᴏᴍᴍᴏɴ",
    2: "🔵 ʀᴀʀᴇ",
    3: "🟡 ʟᴇɢᴇɴᴅᴀʀʏ",
    4: "💮 ꜱᴘᴇᴄɪᴀʟ",
    5: "👹 ᴀɴᴄɪᴇɴᴛ",
    6: "🎐 ᴄᴇʟᴇꜱᴛɪᴀʟ",
    7: "🔮 ᴇᴘɪᴄ",
    8: "🪐 ᴄᴏꜱᴍɪᴄ",
    9: "⚰️ ɴɪɢʜᴛᴍᴀʀᴇ",
    10: "🌬️ ꜰʀᴏꜱᴛʙᴏʀɴ",
    11: "💝 ᴠᴀʟᴇɴᴛɪɴᴇ",
    12: "🌸 ꜱᴘʀɪɴɢ",
    13: "🏖️ ᴛʀᴏᴘɪᴄᴀʟ",
    14: "🍭 ᴋᴀᴡᴀɪɪ",
    15: "🧬 ʜʏʙʀɪᴅ"
}

RARITY_EMOJIS = {
    1: '⚪', 2: '🔵', 3: '🟡', 4: '💮', 5: '👹',
    6: '🎐', 7: '🔮', 8: '🪐', 9: '⚰️', 10: '🌬️',
    11: '💝', 12: '🌸', 13: '🏖️', 14: '🍭', 15: '🧬'
}

# ============ SMALL CAPS MAPPING ============
SMALL_CAPS_MAP = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 'ꜱ', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ꜰ', 'G': 'ɢ',
    'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 'ꜱ', 'T': 'ᴛ', 'U': 'ᴜ',
    'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
    ' ': ' ', ':': ':', '!': '!', '?': '?', '.': '.', ',': ',', '-': '-',
    '(': '(', ')': ')', '[': '[', ']': ']', '{': '{', '}': '}', '=': '=',
    '+': '+', '*': '*', '/': '/', '\\': '\\', '|': '|', '_': '_', '"': '"',
    "'": "'", '`': '`', '~': '~', '@': '@', '#': '#', '$': '$', '%': '%',
    '^': '^', '&': '&', ';': ';', '<': '<', '>': '>', '0': '0', '1': '1',
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8',
    '9': '9'
}

# Pre-compiled translation table for better performance
_SMALL_CAPS_TRANS = str.maketrans(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
    'ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ'
)


# ============ UTILITY FUNCTIONS ============
def to_small_caps(text: str) -> str:
    """Convert text to small caps Unicode characters."""
    if not text:
        return ""
    return str(text).translate(_SMALL_CAPS_TRANS)


def get_rarity_display(rarity) -> str:
    """Get display string for rarity value."""
    if isinstance(rarity, int) and rarity in RARITY_MAP:
        return RARITY_MAP[rarity]
    return str(rarity)


def get_rarity_emoji(rarity) -> str:
    """Get emoji for rarity value."""
    if isinstance(rarity, int) and rarity in RARITY_EMOJIS:
        return RARITY_EMOJIS[rarity]
    return '⚪'


def parse_rarity(rarity_value) -> int:
    """Parse various rarity formats to integer."""
    if rarity_value is None:
        return 1
    
    if isinstance(rarity_value, int):
        return rarity_value if rarity_value in RARITY_MAP else 1
    
    if isinstance(rarity_value, str):
        rarity_str = rarity_value.strip().lower()
        
        if rarity_str.isdigit():
            num = int(rarity_str)
            return num if num in RARITY_MAP else 1
        
        # Check for emoji
        for emoji, num in RARITY_EMOJIS.items():
            if emoji in rarity_str:
                return num
        
        # Check for name
        name_to_int = {
            'common': 1, 'rare': 2, 'legendary': 3, 'special': 4, 'ancient': 5,
            'celestial': 6, 'epic': 7, 'cosmic': 8, 'nightmare': 9, 'frostborn': 10,
            'valentine': 11, 'spring': 12, 'tropical': 13, 'kawaii': 14, 'hybrid': 15,
        }
        if rarity_str in name_to_int:
            return name_to_int[rarity_str]
    
    return 1


# ============ PROGRESS BAR UTILITY ============
def create_progress_bar(percentage: float, width: int = 10) -> str:
    """Create a visual progress bar."""
    filled = int(width * percentage / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {percentage:.1f}%"


# ============ TIME FORMATTING ============
def format_time(seconds: float) -> str:
    """Format seconds into human-readable time."""
    if seconds <= 0:
        return "0s"
    
    from datetime import timedelta
    delta = timedelta(seconds=int(seconds))
    parts = []

    if delta.days > 0:
        parts.append(f"{delta.days}d")

    hours = delta.seconds // 3600
    if hours > 0:
        parts.append(f"{hours}h")

    minutes = (delta.seconds % 3600) // 60
    if minutes > 0:
        parts.append(f"{minutes}m")

    secs = delta.seconds % 60
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)
