from config import logger, configuration
from pathlib import Path

def load_prompt(
    prompt_name: str,
    channel_name: str = configuration["app"]["name"],
    channel_desc: str = configuration["app"]["description"],
    channel_audience: str = configuration["app"]["audience"]
) -> str:
    """ load the prompt from the prompts directory """

    prompt_path = Path(__file__).parent / f"{prompt_name}.md"
    
    try:
        with open(prompt_path, 'r') as f:
            prompt = f.read()
            prompt = prompt.replace("<|channel_name|>", channel_name)
            prompt = prompt.replace("<|channel_desc|>", channel_desc)
            prompt = prompt.replace("<|channel_audience|>", channel_audience)
            
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file {prompt_path} not found.")

    return prompt

def update_prompt(prompt_name: str, prompt: str) -> None:
    """ update the prompt in the prompts directory """
    
    prompt_path = Path(__file__).parent / f"{prompt_name}.md"
    
    try:
        with open(prompt_path, 'w') as f:
            f.write(prompt)
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file {prompt_path} not found.")