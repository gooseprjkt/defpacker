"""
Encoder module for DefPacker - Provides customizable encoding with junk insertion
"""

import re
import random
from typing import Dict, List, Set
from string import ascii_letters, digits


class Encoder:
    """
    Customizable encoder with configurable junk insertion for DefPacker.
    Replaces the kraken algorithm with more junk-like symbols.
    """
    
    def __init__(self, 
                 chars_to_encode: str = None,
                 token_alphabet: str = None,
                 junk_pool: str = None,
                 junk_range: range = None):
        """
        Initialize the encoder with customizable parameters.
        
        Args:
            chars_to_encode: Characters to encode (defaults to alphanumeric + common symbols)
            token_alphabet: Characters to use for encoding tokens (defaults to junk-like symbols)
            junk_pool: Characters to insert as junk (defaults to junk-like symbols)
            junk_range: Range for fallback junk characters
        """
        if chars_to_encode is None:
            chars_to_encode = (
                ascii_letters + digits +
                " .,!?;:-\"'()[]{}@#$%^&*_+=|\\/<>" +
                "«»„“”‘’—–…№"
            )
        
        if token_alphabet is None:
            # Use more junk-like symbols instead of emojis
            token_alphabet = (
                "¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿"
                "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß"
                "àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ"
                "ЀЁЂЃЄЅІЇЈЉЊЋЌЍЎЏАБВГДЕЖЗИЙКЛМНОП"
            )
        
        if junk_pool is None:
            # Much more junk characters for maximum obfuscation
            junk_pool = (
                "¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿"
                "×÷†‡•‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ"
                "¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿"
                "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß"
                "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
                "ĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽž"
                "ƒǺǻǼǽǾǿȘșȚțȞȟȠȡȤȥȦȧȨȩȪȫȬȭȮȯȰȱȲȳȴȵȶȷȸȹȺȻȼȽȾȿɀɁɂɃɄɅɆɇɈɉɊɋɌɍɎɏ"
                "΄΅Ά·ΈΉΊΌΎΏΐΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩΪΫάέήίΰαβγδεζηθικλμνξοπρςστυφχψωϊϋόύώϐϑϒϓϔϕϖϗϘϙϚϛϜϝϞϟϠϡϢϣϤϥϦϧϨϩϪϫϬϭϮϯϰϱϲϳϴϵ϶ϷϸϹϺϻϼϽϾϿ"
            )
        
        if junk_range is None:
            junk_range = range(0x2000, 0x2100)  # Additional Unicode range
        
        if len(token_alphabet) < 50:
            raise RuntimeError("Недостаточно символов в TOKEN_ALPHABET")

        self.encoded_map: Dict[str, str] = {}
        used_tokens: Set[str] = set()
        token_length = 4

        # Use a completely deterministic approach to ensure consistent token generation
        import hashlib
        for i, char in enumerate(chars_to_encode):
            # Generate a deterministic token based on the character and its position
            char_hash = hashlib.sha256(f"defpacker_token_{char}_{i}".encode()).hexdigest()
            
            # Generate token deterministically from the hash
            token = ""
            hash_idx = 0
            for _ in range(token_length):
                # Use part of the hash to pick a character from token_alphabet
                hex_pair = char_hash[hash_idx:hash_idx+2]
                val = int(hex_pair, 16) % len(token_alphabet)
                token += token_alphabet[val]
                hash_idx = (hash_idx + 2) % len(char_hash)  # Cycle through hash
            
            # Ensure uniqueness by appending a counter if needed
            counter = 0
            original_token = token
            while token in used_tokens:
                # If token already exists, modify it using the counter
                counter_hex = hashlib.sha256(f"counter_{counter}_{original_token}".encode()).hexdigest()
                hex_pair = counter_hex[0:2]
                val = int(hex_pair, 16) % len(token_alphabet)
                token = original_token[:-1] + token_alphabet[val]  # Change last character
                counter += 1
                if counter > 1000:  # Safety check
                    raise RuntimeError(f"Could not generate unique token for character: {repr(char)}")
            
            used_tokens.add(token)
            self.encoded_map[char] = token

        used_chars = set(ch for v in self.encoded_map.values() for ch in v)
        used_chars.update(self.encoded_map.keys())
        # Make sure junk characters are not part of any token
        self.safe_junk = [ch for ch in junk_pool if ch not in used_chars]
        # Additionally, ensure junk characters are not in token_alphabet to prevent conflicts
        token_chars = set(token_alphabet)
        self.safe_junk = [ch for ch in self.safe_junk if ch not in token_chars]
        if not self.safe_junk:
            fallback = [chr(i) for i in junk_range if chr(i) not in used_chars and chr(i) not in token_chars]
            self.safe_junk = fallback[:20] or ['~', '^', '`']

        self.decoded_map = {v: k for k, v in self.encoded_map.items()}
        if len(self.decoded_map) != len(self.encoded_map):
            raise ValueError("Обнаружены коллизии в токенах")

        self.sorted_tokens: List[str] = sorted(self.decoded_map.keys(), key=len, reverse=True)
        escaped = [re.escape(tok) for tok in self.sorted_tokens]
        self.token_pattern = re.compile("|".join(escaped))

    def encode(self, text: str, junk_level: float = 0.3) -> str:
        """
        Encode text with configurable junk insertion.
        
        Args:
            text: Text to encode
            junk_level: Level of junk insertion (0.0 to 1.0)
            
        Returns:
            Encoded text with junk
        """
        if not text:
            return ""
        
        result = []
        junk_interval = max(2, int(1.0 / (junk_level + 1e-9))) if junk_level > 0 else float('inf')

        for i, char in enumerate(text):
            token = self.encoded_map.get(char, char)
            result.append(token)
            if junk_level > 0 and (i + 1) % junk_interval == 0 and self.safe_junk:
                # Insert fewer junk characters to avoid token confusion
                num_junk = random.randint(1, 2)  # Reduced from 1-3 to 1-2
                for _ in range(num_junk):
                    result.append(random.choice(self.safe_junk))
        return "".join(result)

    def decode(self, encoded: str) -> str:
        """
        Decode encoded text.
        
        Args:
            encoded: Encoded text with junk
            
        Returns:
            Decoded original text
        """
        if not encoded:
            return ""
        
        # Replace all tokens with their original characters, leaving junk characters
        # Then remove the junk characters
        result = []
        last_end = 0
        
        for match in self.token_pattern.finditer(encoded):
            # Add the token's original character
            token = match.group()
            original_char = self.decoded_map.get(token, "?")
            result.append(original_char)
        
        return "".join(result)