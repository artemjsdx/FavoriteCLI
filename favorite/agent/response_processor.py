"""
favorite/agent/response_processor.py
Processing and cleaning LLM responses.
"""
import re

def strip_thinking_blocks(text: str) -> str:
  """
  Strips <thinking>...</thinking> blocks from the text.
  Handles nested blocks (though unlikely from LLM) and unclosed blocks.
  """
  # Simple regex for most cases
  text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
  
  # Handle unclosed <thinking> tag at the end (common in streaming or truncated responses)
  if '<thinking>' in text and '</thinking>' not in text:
      text = text.split('<thinking>')[0]
      
  return text.strip()
