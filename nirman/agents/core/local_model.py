"""
NirmanAI - Local GPU Model Loader (Singleton)
==============================================
Loads the fine-tuned QLoRA adapter on top of the cached 4-bit base model
directly on the local GPU (RTX A2000 12GB).

This module uses a singleton pattern so the model is loaded ONCE into GPU memory
and reused across all generation calls — no repeated loading overhead.

Supported base models:
- unsloth/Qwen2.5-7B-Instruct-bnb-4bit (pre-quantized, ~4.5 GB, cached locally)

Environment Variables:
- LOCAL_BASE_MODEL: Base model ID (default: unsloth/Qwen2.5-7B-Instruct-bnb-4bit)
- LOCAL_ADAPTER_DIR: Path to LoRA adapter (default: ./nirmanai_adapter)
- LOCAL_MAX_NEW_TOKENS: Max tokens to generate (default: 4096)
"""

import os
import sys
import json
import logging
import threading
from typing import Optional

logger = logging.getLogger("nirman.local_model")

# Windows UTF-8 stdout fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class LocalModelLoader:
    """Singleton loader for the fine-tuned NirmanAI model on local GPU.
    
    Loads the model once into GPU memory and provides a generate() method
    for inference. Thread-safe via a lock.
    """

    _instance: Optional["LocalModelLoader"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        base_model: Optional[str] = None,
        adapter_dir: Optional[str] = None,
    ):
        if self._initialized:
            return
        
        self.base_model_id = base_model or os.getenv(
            "LOCAL_BASE_MODEL", "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
        )
        self.adapter_dir = adapter_dir or os.getenv(
            "LOCAL_ADAPTER_DIR", "./nirmanai_adapter"
        )
        self.max_new_tokens = int(os.getenv("LOCAL_MAX_NEW_TOKENS", "4096"))
        
        self.model = None
        self.tokenizer = None
        self._initialized = True

    def _load_model(self):
        """Lazily loads the model + adapter into GPU memory on first call."""
        if self.model is not None:
            return

        with self._lock:
            if self.model is not None:
                return

            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from peft import PeftModel

            logger.info(f"🚀 Loading local model: {self.base_model_id}")
            logger.info(f"   Adapter: {self.adapter_dir}")

            # Load tokenizer from adapter dir (has the fine-tuned special tokens)
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.adapter_dir, trust_remote_code=True
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Load base model (pre-quantized 4-bit, no BitsAndBytesConfig needed)
            if "bnb-4bit" in self.base_model_id:
                base = AutoModelForCausalLM.from_pretrained(
                    self.base_model_id,
                    device_map="auto",
                    trust_remote_code=True,
                )
            else:
                from transformers import BitsAndBytesConfig
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=(
                        torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                    ),
                )
                base = AutoModelForCausalLM.from_pretrained(
                    self.base_model_id,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=True,
                )

            # Load LoRA adapter on top
            self.model = PeftModel.from_pretrained(base, self.adapter_dir)
            self.model.eval()

            # Log GPU memory usage
            if torch.cuda.is_available():
                allocated_gb = torch.cuda.memory_allocated() / (1024 ** 3)
                logger.info(f"✅ Model loaded on GPU. VRAM used: {allocated_gb:.1f} GB")
            else:
                logger.warning("⚠️ CUDA not available, model loaded on CPU (will be slow)")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text using the local fine-tuned model.
        
        Args:
            system_prompt: System instruction for the model
            user_prompt: User's architecture request
            
        Returns:
            Raw generated text from the model
        """
        import torch
        
        self._load_model()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        prompt_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt_text, return_tensors="pt").to(self.model.device)

        logger.info(f"🧠 Generating with local model (max_new_tokens={self.max_new_tokens})...")

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=0.2,
                top_p=0.9,
                repetition_penalty=1.05,
                do_sample=True,
            )

        # Decode only the generated part (exclude the prompt tokens)
        generated_tokens = outputs[0][len(inputs["input_ids"][0]):]
        result_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

        logger.info(f"✅ Local model generated {len(generated_tokens)} tokens.")
        return result_text

    def is_available(self) -> bool:
        """Check if the adapter directory exists and CUDA is available."""
        adapter_exists = os.path.isdir(self.adapter_dir)
        try:
            import torch
            cuda_available = torch.cuda.is_available()
        except ImportError:
            cuda_available = False
        return adapter_exists and cuda_available
