"""
Base class for all AI analyzer agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import anthropic
from config import settings
import logging

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """Base class for all Claude AI analyzers"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.filter_model = settings.filter_model  # Haiku for quick filtering
        self.analysis_model = settings.analysis_model  # Sonnet for deep analysis

    def _call_claude(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        system: Optional[str] = None
    ) -> str:
        """
        Call Claude API with given prompt
        Returns the response text
        """
        try:
            model_to_use = model or self.analysis_model

            logger.debug(f"Calling Claude ({model_to_use})")

            message = self.client.messages.create(
                model=model_to_use,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else "You are a helpful AI assistant analyzing startup ideas and market opportunities.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            logger.debug(f"Claude response length: {len(response_text)} chars")

            return response_text

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            raise

    def _quick_filter(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Quick yes/no filter using Haiku (cheap and fast)
        """
        return self._call_claude(
            prompt=prompt,
            model=self.filter_model,
            max_tokens=500,
            temperature=0.3,  # Lower temperature for more consistent filtering
            system=system
        )

    def _deep_analysis(
        self,
        prompt: str,
        max_tokens: int = 2000,
        system: Optional[str] = None
    ) -> str:
        """
        Deep analysis using Sonnet (more expensive but better quality)
        """
        return self._call_claude(
            prompt=prompt,
            model=self.analysis_model,
            max_tokens=max_tokens,
            temperature=0.7,
            system=system
        )

    @abstractmethod
    def analyze(self, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method - must be implemented by child classes
        Returns dictionary with analysis results
        """
        pass
