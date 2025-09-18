# src/analysis/llm_client.py
import os
import requests
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import logging
from dataclasses import dataclass

logger = logging.getLogger("market_aggregator.ai")

import yaml
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# 🎛️  MODEL CONFIGURATION - NOW IN ai_config.yml
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProviderConfig:
    """Configuration for an AI provider"""
    provider: str
    model: str
    reasoning_effort: str = "medium"  # OpenAI only
    verbosity: str = "medium"         # OpenAI only

def load_ai_config() -> List[Dict]:
    """
    Loads the AI provider pipeline from ai_config.yml
    """
    config_path = Path(__file__).parent.parent.parent / 'ai_config.yml'
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if "pipeline" not in config or not isinstance(config["pipeline"], list):
            raise ValueError("ai_config.yml is missing 'pipeline' list or it's not a list")

        return config["pipeline"]
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {e}")
        raise

# ═══════════════════════════════════════════════════════════════
# 🔧 EXCEPTIONS AND BASE CLASSES
# ═══════════════════════════════════════════════════════════════

class ProviderError(Exception):
    """Raised when an AI provider fails to generate analysis"""
    def __init__(self, provider_name: str, message: str, original_error: Optional[Exception] = None):
        self.provider_name = provider_name
        self.original_error = original_error
        super().__init__(f"{provider_name}: {message}")

class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def generate_analysis(self, prompt: str) -> str:
        """Generate analysis from the given prompt. Raises ProviderError on failure."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this provider"""
        pass
    
    def cleanup(self):
        """Clean up resources (override if needed)"""
        pass

# ═══════════════════════════════════════════════════════════════
# 🤖 PROVIDER IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════

class OpenAIProvider(AIProvider):
    """OpenAI API provider implementation with GPT-5 support"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"OpenAI provider initialized: {config.model}")

    def generate_analysis(self, prompt: str) -> str:
        """Generate analysis using OpenAI API"""
        try:
            logger.info(f"Sending request to OpenAI {self.config.model}...")
            
            data = {
                "model": self.config.model,
                "messages": [
                    {
                        "role": "system",
                        "content": """You are a professional financial market analyst. Provide comprehensive analysis using STRICT MARKDOWN formatting:

FORMATTING REQUIREMENTS:
- Use ## for main sections (e.g., ## SECTION 1 - MARKET PERFORMANCE)
- Use ### for subsections (e.g., ### Looking Ahead)
- Use **bold** for emphasis and important terms
- Use - for bullet points with proper spacing
- Use numbered lists (1., 2., 3.) for structured content
- Always include blank lines between sections
- Use | for tables when showing market data

Provide professional, comprehensive analysis with deep reasoning while maintaining this exact formatting structure."""
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_completion_tokens": 8000
            }
            
            # GPT-5 specific parameters
            if self.config.model.startswith('gpt-5'):
                data["verbosity"] = self.config.verbosity
                data["reasoning_effort"] = self.config.reasoning_effort
            else:
                data["temperature"] = 0.7
                data["top_p"] = 0.9
            
            response = self.session.post(
                'https://api.openai.com/v1/chat/completions',
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content')
                
                if not content or not content.strip():
                    raise ProviderError(
                        self.get_provider_name(),
                        "Received empty response from API"
                    )
                
                # Log usage
                usage = result.get('usage', {})
                logger.info(f"OpenAI usage - total tokens: {usage.get('total_tokens', 0)}")
                
                return content
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                raise ProviderError(self.get_provider_name(), error_msg)

        except requests.exceptions.RequestException as e:
            raise ProviderError(self.get_provider_name(), f"Network error: {str(e)}", e)
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(self.get_provider_name(), f"Unexpected error: {str(e)}", e)

    def get_provider_name(self) -> str:
        return f"OpenAI {self.config.model}"
    
    def cleanup(self):
        if hasattr(self, 'session'):
            self.session.close()

class GeminiProvider(AIProvider):
    """Google Gemini API provider implementation"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        logger.info(f"Gemini provider initialized: {config.model}")

    def generate_analysis(self, prompt: str) -> str:
        """Generate analysis using Google Gemini API"""
        try:
            logger.info(f"Sending request to Gemini {self.config.model}...")
            
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"You are a professional financial market analyst. Provide comprehensive analysis with clear structure and reasoning.\n\n{prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 12000,
                    "candidateCount": 1
                }
            }
            
            url = f"{self.base_url}/models/{self.config.model}:generateContent"
            params = {"key": self.api_key}
            
            response = self.session.post(url, params=params, json=data, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        content = candidate['content']['parts'][0].get('text', '')
                        
                        if not content or not content.strip():
                            raise ProviderError(
                                self.get_provider_name(),
                                "Received empty response from API"
                            )
                        
                        return content
                
                raise ProviderError(self.get_provider_name(), "Unexpected response structure")
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                raise ProviderError(self.get_provider_name(), error_msg)

        except requests.exceptions.RequestException as e:
            raise ProviderError(self.get_provider_name(), f"Network error: {str(e)}", e)
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(self.get_provider_name(), f"Unexpected error: {str(e)}", e)

    def get_provider_name(self) -> str:
        return f"Gemini {self.config.model}"
    
    def cleanup(self):
        if hasattr(self, 'session'):
            self.session.close()

class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider implementation"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        })
        
        logger.info(f"Anthropic provider initialized: {config.model}")

    def generate_analysis(self, prompt: str) -> str:
        """Generate analysis using Anthropic API"""
        try:
            logger.info(f"Sending request to Anthropic {self.config.model}...")
            
            data = {
                'model': self.config.model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 4000,
                'temperature': 0.7
            }
            
            response = self.session.post(
                'https://api.anthropic.com/v1/messages',
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['content'][0]['text']
                
                if not content or not content.strip():
                    raise ProviderError(
                        self.get_provider_name(),
                        "Received empty response from API"
                    )
                
                return content
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                raise ProviderError(self.get_provider_name(), error_msg)

        except requests.exceptions.RequestException as e:
            raise ProviderError(self.get_provider_name(), f"Network error: {str(e)}", e)
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(self.get_provider_name(), f"Unexpected error: {str(e)}", e)

    def get_provider_name(self) -> str:
        return f"Anthropic {self.config.model}"
    
    def cleanup(self):
        if hasattr(self, 'session'):
            self.session.close()

# ═══════════════════════════════════════════════════════════════
# 🧠 AI CLIENT WITH FALLBACK SUPPORT
# ═══════════════════════════════════════════════════════════════

class AIClient:
    """
    Main AI client with automatic fallback support.
    Tries providers from the pipeline in ai_config.yml in order.
    """
    
    def __init__(self):
        self.providers: List[AIProvider] = []
        
        # Load AI provider configuration from YAML file
        ai_pipeline = load_ai_config()

        # Create and add providers based on the configuration
        for i, provider_config_dict in enumerate(ai_pipeline):
            role = "Primary" if i == 0 else f"Fallback {i}"
            try:
                # Use ** to unpack dictionary into dataclass fields
                config = ProviderConfig(**provider_config_dict)
                provider = self._create_provider(config)
                self.providers.append(provider)
                logger.info(f"🤖 {role} provider ready: {provider.get_provider_name()}")
            except (ValueError, TypeError) as e:
                # Catch errors from missing keys or bad provider names
                logger.error(f"Failed to initialize {role} provider with config {provider_config_dict}: {e}")
        
        if not self.providers:
            logger.warning("No AI providers were successfully initialized - will use basic analysis only")

    def _create_provider(self, config: ProviderConfig) -> AIProvider:
        """Factory method to create provider instances"""
        provider_map = {
            "openai": OpenAIProvider,
            "gemini": GeminiProvider,
            "anthropic": AnthropicProvider
        }
        
        provider_class = provider_map.get(config.provider)
        if not provider_class:
            raise ValueError(f"Unknown provider: {config.provider}")
        
        return provider_class(config)

    def generate_analysis(self, prompt: str) -> tuple[str, str]:
        """
        Generate analysis with automatic fallback.
        
        Returns:
            Tuple of (analysis_text, provider_name_used)
        """
        # Try each provider in order
        for i, provider in enumerate(self.providers):
            try:
                provider_name = provider.get_provider_name()
                if i > 0:  # Mark fallback providers
                    provider_name += " (Fallback)"
                
                logger.info(f"Attempting analysis with: {provider.get_provider_name()}")
                analysis = provider.generate_analysis(prompt)
                
                if i > 0:  # Log successful fallback
                    logger.info(f"Successfully generated analysis using fallback provider")
                
                return analysis, provider_name
                
            except ProviderError as e:
                logger.warning(f"Provider failed: {e}")
                if i == len(self.providers) - 1:  # Last provider failed
                    logger.error("All AI providers failed")
        
        # All providers failed - return basic analysis
        logger.error("Generating basic analysis as final fallback")
        return self._create_basic_analysis(), "Basic Analysis (No AI)"

    def _create_basic_analysis(self) -> str:
        """Create a basic analysis when all AI providers fail"""
        from datetime import datetime
        
        return f"""## MARKET ANALYSIS - {datetime.now().strftime('%B %d, %Y')}

**⚠️ Notice:** AI analysis temporarily unavailable. Please check provider configurations.

## SYSTEM STATUS
- All configured AI providers are currently unavailable
- This may be due to API key issues, network problems, or service outages
- Please verify your API keys and network connectivity

## RECOMMENDATIONS
- Check your environment variables for API keys
- Verify network connectivity to AI provider endpoints
- Monitor provider status pages for service interruptions
- Consider configuring additional fallback providers

**Next Steps:** Resolve provider issues to restore full AI-powered analysis capabilities."""

    def get_available_providers(self) -> List[str]:
        """Get list of successfully initialized provider names"""
        return [provider.get_provider_name() for provider in self.providers]

    def __del__(self):
        """Clean up all provider resources"""
        for provider in self.providers:
            try:
                provider.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up provider {provider.get_provider_name()}: {e}")
