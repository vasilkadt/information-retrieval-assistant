"""
Language Validation Module

Ensures that questions are in the Bulgarian language.
This chatbot is designed specifically for Bulgarian IR course materials.
"""

from langdetect import detect, LangDetectException
from typing import Dict

class LanguageValidator:
    """Confirms that text is in Bulgarian language"""
    
    SUPPORTED_LANGUAGE = "bg"
    SUPPORTED_LANGUAGE_NAME = "български"
    
    # Accept both Bulgarian and Macedonian (langdetect often confuses them)
    # They use the same Cyrillic script and are very similar
    ACCEPTED_LANGUAGES = {"bg", "mk"}
    
    ERROR_MESSAGES = {
        "bg": "Моля, задайте въпроса си на български език.",
        "en": "This chatbot supports Bulgarian language only. Please ask your question in Bulgarian.",
        "default": "Този чатбот поддържа само български език. Моля, задайте въпроса си на български."
    }
    
    def __init__(self, min_length: int = 5):
        """
        Initialize language validator
        
        Args:
            min_length: Minimum text length to validate
        """
        self.min_length = min_length
    
    def validate(self, text: str) -> Dict:
        """
        Validate that text is in Bulgarian
        
        Args:
            text: Input text to validate
        
        Returns:
            Dict with a validation result:
            {
                "valid": bool,
                "language": str,
                "confidence": float,
                "message": str
            }
        """

        if len(text.strip()) < self.min_length:
            return {
                "valid": False,
                "language": "unknown",
                "confidence": 0.0,
                "message": f"Въпросът е твърде кратък (минимум {self.min_length} символа)."
            }
        
        try:

            detected_lang = detect(text)
            
            # Accept Bulgarian and Macedonian (often misclassified due to similarity)
            if detected_lang in self.ACCEPTED_LANGUAGES:
                return {
                    "valid": True,
                    "language": "bg",  # Treat as Bulgarian
                    "confidence": 1.0,
                    "message": "✓ Език: български"
                }
            
            # Also check if text contains Cyrillic characters (likely Bulgarian)
            cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
            if cyrillic_count > len(text) * 0.3:  # More than 30% Cyrillic
                return {
                    "valid": True,
                    "language": "bg",
                    "confidence": 0.8,
                    "message": "✓ Език: български"
                }
            
            error_message = self._get_error_message(detected_lang)
            
            return {
                "valid": False,
                "language": detected_lang,
                "confidence": 0.0,
                "message": error_message
            }
        
        except LangDetectException:
            return {
                "valid": False,
                "language": "unknown",
                "confidence": 0.0,
                "message": "Не можах да разпозная езика. Моля, използвайте български език."
            }
    
    def _get_error_message(self, detected_lang: str) -> str:
        """
        Get the appropriate error message based on detected language
        
        Args:
            detected_lang: Detected language code (e.g., 'en', 'de', 'ru')
        
        Returns:
            Error message in the appropriate language
        """

        message = self.ERROR_MESSAGES.get(detected_lang, self.ERROR_MESSAGES["default"])
        
        lang_names = {
            "en": "English",
            "de": "German",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian",
            "ru": "Russian",
            "el": "Greek",
            "tr": "Turkish",
            "sr": "Serbian",
            "mk": "Macedonian",
            "ro": "Romanian"
        }
        
        detected_name = lang_names.get(detected_lang, detected_lang.upper())
        
        return f"⚠️ Detected language: {detected_name}\n\n{message}"
    
    def is_bulgarian(self, text: str) -> bool:
        """
        Simple check if the text is Bulgarian
        
        Args:
            text: Text to check
        
        Returns:
            True if Bulgarian, False otherwise
        """
        result = self.validate(text)
        return result["valid"]


# Global validator instance
_validator = None

def get_validator() -> LanguageValidator:
    """Get or create the global validator instance"""
    global _validator
    if _validator is None:
        _validator = LanguageValidator()
    return _validator


def validate_bulgarian(text: str) -> Dict:
    """
    Quick validation function
    
    Args:
        text: Text to validate
    
    Returns:
        Validation result dictionary
    """
    validator = get_validator()
    return validator.validate(text)