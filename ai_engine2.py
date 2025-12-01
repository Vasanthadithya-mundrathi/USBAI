# File: ai_engine.py
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
# Set encoding to utf-8 for handling emojis and other Unicode characters
os.environ["PYTHONIOENCODING"] = "utf-8"

# Configure native BLAS/OpenMP thread environment variables early so
# that libraries loaded by Python / PyTorch will pick them up.
# Honor the `USBAI_NUM_THREADS` environment variable if provided.
env_threads = os.environ.get("USBAI_NUM_THREADS")
num_cores_for_env = os.cpu_count() or 4
if env_threads:
    try:
        desired_threads_env = int(env_threads)
    except ValueError:
        desired_threads_env = num_cores_for_env
else:
    desired_threads_env = num_cores_for_env

os.environ.setdefault("OMP_NUM_THREADS", str(desired_threads_env))
os.environ.setdefault("MKL_NUM_THREADS", str(desired_threads_env))
os.environ.setdefault("OPENBLAS_NUM_THREADS", str(desired_threads_env))

import sys
import logging
import torch
import time
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
import re
import io
from typing import Optional, Dict, List, Union, Tuple
import gc  # Add garbage collection

# Try to import sympy, fall back to eval if not available
try:
    from sympy import sympify
    USE_SYMPY = True
except ImportError:
    USE_SYMPY = False
    print("SymPy not installed. Falling back to eval() for math evaluation. For better accuracy, install SymPy: pip install sympy")

# Enable KV cache optimization if using a supported version of transformers
try:
    from transformers import PreTrainedModel
    KV_CACHE_AVAILABLE = hasattr(PreTrainedModel, "_get_use_cache_orig")
except ImportError:
    KV_CACHE_AVAILABLE = False

# Set UTF-8 encoding globally for standard output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Limit PyTorch threads to avoid CPU overload but allow scaling based on CPU cores
# Use environment variable `USBAI_NUM_THREADS` to override the default behavior.
NUM_CORES = os.cpu_count() or 4
env_threads = os.environ.get("USBAI_NUM_THREADS")
if env_threads:
    try:
        desired_threads = int(env_threads)
    except ValueError:
        desired_threads = NUM_CORES
else:
    # Default to the machine's logical core count if not specified
    desired_threads = NUM_CORES

NUM_THREADS = max(1, desired_threads)
torch.set_num_threads(NUM_THREADS)
print(f"PyTorch threads configured: {NUM_THREADS} (requested={desired_threads}, cpu_count={NUM_CORES})")

class USBAIEngine:
    def __init__(self, base_path: str = "E:\\USBAI", model_name: str = "gemma-3-1b-it"):
        self.base_path = Path(base_path)
        self.model_name = model_name
        self.setup_logging()
        self.model = None
        self.tokenizer = None
        self.load_model()
        self.setup_techniques()
        self.model_meta = self._get_model_metadata()

    def _get_model_metadata(self) -> Dict[str, any]:
        """Get metadata for the current model to optimize prompting and generation."""
        model_lower = self.model_name.lower()
        meta = {
            "context_length": 2048,  # Default for most models
            "system_token": "",
            "formatting_style": "general",
            "is_chat_model": True
        }
        
        # Model-specific optimizations
        if "gemma" in model_lower:
            meta["context_length"] = 8192
            meta["formatting_style"] = "gemma"
        elif "llama" in model_lower:
            meta["context_length"] = 4096
            meta["formatting_style"] = "llama"
        elif "phi" in model_lower:
            meta["context_length"] = 2048
            meta["formatting_style"] = "phi"
        elif "deepseek" in model_lower:
            meta["context_length"] = 4096
            meta["formatting_style"] = "deepseek"
            
        return meta

    def setup_logging(self):
        """Set up logging to a file."""
        log_path = self.base_path / "logs" / "usbai.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=str(log_path),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'  # Ensure UTF-8 encoding for log files
        )
        logging.info("Logging initialized.")

    def load_model(self):
        """Load the specified model and tokenizer with optimizations."""
        try:
            model_dir = self.base_path / "models" / self.model_name
            if not model_dir.exists():
                raise FileNotFoundError(f"Model directory {model_dir} not found")

            # Detect best available device (CUDA if available, otherwise CPU)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {self.device}")
            logging.info(f"Using device: {self.device}")

            # Load tokenizer with explicit UTF-8 encoding
            print(f"Loading tokenizer from {model_dir}...")
            start_time = time.time()
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(model_dir),
                trust_remote_code=True,
                use_fast=True,  # Use fast tokenizers when available
                padding_side="left"  # Padding on left side for causal LM
            )
            
            # Ensure pad token is set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            # Ensure all special tokens are properly set
            if not hasattr(self.tokenizer, "sep_token") or self.tokenizer.sep_token is None:
                self.tokenizer.sep_token = self.tokenizer.eos_token
                
            print(f"Tokenizer loaded in {time.time() - start_time:.2f} seconds")
            logging.info(f"Tokenizer loaded in {time.time() - start_time:.2f} seconds")

            # Load model with optimizations
            print(f"Loading model from {model_dir}...")
            start_time = time.time()
            
            # Determine best torch dtype based on device
            torch_dtype = torch.float16
            if self.device == "cpu":
                # Use bfloat16 if available (better for CPUs) or fall back to float32
                torch_dtype = torch.bfloat16 if torch.cpu.is_available() and hasattr(torch, 'bfloat16') else torch.float32
            
            self.model = AutoModelForCausalLM.from_pretrained(
                str(model_dir),
                trust_remote_code=True,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
                device_map="auto"
            )

            # Enable gradient checkpointing to reduce memory usage
            if hasattr(self.model, 'gradient_checkpointing_enable'):
                self.model.gradient_checkpointing_enable()
                logging.info("Gradient checkpointing enabled for memory optimization")
                
            # Enable KV cache if available
            if KV_CACHE_AVAILABLE:
                logging.info("KV cache optimization enabled")
                
            # Move model to evaluation mode
            self.model.eval()
            
            # Run garbage collection to free memory after loading
            gc.collect()
            torch.cuda.empty_cache() if torch.cuda.is_available() else None

            print(f"Model loaded in {time.time() - start_time:.2f} seconds")
            logging.info(f"Model loaded in {time.time() - start_time:.2f} seconds")

        except Exception as e:
            logging.error(f"Model loading failed: {e}")
            raise Exception(f"Model loading failed: {e}")

    def setup_techniques(self):
        """Initialize caching and other techniques."""
        self.cache = {}  # Simple caching mechanism for repeated queries
        self.generation_config = {
            # Default generation parameters, will be overridden based on query type
            "max_new_tokens": 300,
            "min_length": 5,
            "do_sample": True,  # Balanced approach - some creativity but mostly deterministic
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 50,
            "repetition_penalty": 1.1,
            "no_repeat_ngram_size": 3
        }
        logging.info("Techniques initialized: caching enabled.")

    def is_math_query(self, text: str) -> bool:
        """Check if the query contains a mathematical expression."""
        # Remove "solve" prefix if present and strip whitespace
        text = text.lower().replace("solve", "").strip()
        # Match patterns like "number operator number" with optional parentheses
        # Improved regex to catch more math patterns
        math_pattern = r'^[\s\d\+\-\*/\^\(\)\.\%=<>!&|]+$'
        is_match = bool(re.match(math_pattern, text))
        logging.info(f"Math query detection for '{text}': {is_match}")
        return is_match

    def extract_and_evaluate_math(self, text: str) -> Optional[float]:
        """Extract and evaluate a mathematical expression from the text."""
        try:
            # Remove "solve" prefix if present
            text = text.lower().replace("solve", "").strip()
            # Sanitize the input: only allow numbers, operators, parentheses, and spaces
            sanitized = re.sub(r'[^0-9\+\-\*/\^\(\)\.\s]', '', text)
            if not sanitized:
                logging.error("Sanitized expression is empty.")
                return None

            # Replace ^ with ** for exponentiation
            sanitized = sanitized.replace('^', '**')
            logging.info(f"Sanitized math expression: {sanitized}")

            # Evaluate the expression with proper order of operations
            if USE_SYMPY:
                result = float(sympify(sanitized))
            else:
                # Fallback to eval if SymPy is not available
                result = eval(sanitized, {"__builtins__": None}, {"**": pow})
            logging.info(f"Evaluated result: {result}")
            return result
        except Exception as e:
            logging.error(f"Math evaluation failed: {e}")
            return None
            
    def is_response_relevant(self, question: str, response: str) -> bool:
        """Check if the response is relevant to the question."""
        # For very short or greeting-type questions, always return true
        if len(question) < 10 or any(greeting in question.lower() for greeting in ["hello", "hi ", "hey", "greetings", "how are you"]):
            return True
            
        question_lower = question.lower()
        response_lower = response.lower()

        # Extract key terms from the question (nouns, verbs, adjectives)
        # This is a simple approach - could be improved with NLP
        words = question_lower.split()
        key_terms = [w for w in words if len(w) > 3 and w not in ["what", "when", "where", "which", "how", "that", "with", "from", "this", "these", "those", "a", "an", "the"]]
        
        # Check if at least one key term from the question appears in the response
        if key_terms:
            return any(term in response_lower for term in key_terms)

        # Define expected keywords for specific question types
        if "colour" in question_lower or "color" in question_lower:
            return any(color in response_lower for color in ["red", "green", "blue", "yellow", "pink", "purple", "black", "white", "orange", "brown"])
        elif "alphabet" in question_lower:
            return "letter" in response_lower or any(str(i) in response_lower for i in range(10))
        elif "elon musk" in question_lower:
            return "elon" in response_lower or "musk" in response_lower or "tesla" in response_lower or "spacex" in response_lower
        elif "days" in question_lower and "week" in question_lower:
            return "day" in response_lower or "week" in response_lower or "7" in response_lower
        elif "who is" in question_lower:
            return any(word in response_lower for word in question_lower.split()) or "is" in response_lower
        return True  # Default to true if no specific check

    def validate_response(self, question: str, response: str) -> bool:
        """Validate the response for factual correctness."""
        question_lower = question.lower()
        response_lower = response.lower()

        # Specific validation rules
        if "days" in question_lower and "week" in question_lower:
            return "7" in response_lower  # Must contain the correct number
        elif "alphabet" in question_lower:
            return "26" in response_lower  # English alphabet has 26 letters
        elif "months" in question_lower and "year" in question_lower:
            return "12" in response_lower  # A year has 12 months
        elif "water" in question_lower and "boil" in question_lower:
            return "100" in response_lower or "212" in response_lower  # Boiling point of water
        return True  # Default to true if no specific validation

    def format_prompt(self, text: str, is_math: bool = False, result: Optional[float] = None) -> str:
        """Format prompt based on model type and query."""
        style = self.model_meta["formatting_style"]
        
        if is_math and result is not None:
            if style == "gemma":
                return (
                    "<start_of_turn>user\n"
                    f"{text}"
                    "\n<end_of_turn>\n"
                    "<start_of_turn>model\n"
                    f"The result of {text} is {result}. Following the proper order of operations (PEMDAS/BODMAS), here's how to solve this expression step by step:\n"
                )
            else:
                # Generic approach for other models
                return (
                    f"User: {text}\n"
                    f"Assistant: The result of {text} is {result}. Following the proper order of operations (PEMDAS/BODMAS), here's how to solve this expression step by step:\n"
                )
        
        # For regular queries
        if style == "gemma":
            return (
                "<start_of_turn>user\n"
                f"{text}"
                "\n<end_of_turn>\n"
                "<start_of_turn>model\n"
            )
        elif style == "llama":
            return (
                "User\n"
                f"{text}\n"
                "\nAssistant\n"
            )
        elif style == "phi":
            return (
                "Instruct: Answer the following question accurately, clearly, and helpfully.\n"
                f"Human: {text}\n"
                "Assistant: "
            )
        elif style == "deepseek":
            return (
                "<｜begin▁of▁sentence｜>"
                "Human: I need a detailed and accurate answer to the following question.\n"
                f"{text}\n\n"
                "Assistant: "
            )
        else:
            # Generic approach
            return (
                "USER: I need an accurate answer to this question.\n"
                f"{text}\n"
                "ASSISTANT: "
            )

    def optimize_generation_config(self, is_math: bool, is_factual: bool) -> Dict[str, any]:
        """Optimize generation parameters based on query type."""
        config = self.generation_config.copy()
        
        if is_math:
            # For math problems, use more deterministic settings
            config["do_sample"] = False
            config["temperature"] = None  # Use greedy decoding
            config["top_p"] = None
            config["top_k"] = None
            config["max_new_tokens"] = 150  # Shorter responses for math
        elif is_factual:
            # For factual questions, reduce randomness but keep some flexibility
            config["do_sample"] = True
            config["temperature"] = 0.5  # Lower temperature for more deterministic output
            config["top_p"] = 0.85
            config["top_k"] = 40
            config["repetition_penalty"] = 1.2  # Slightly higher to avoid repetition
        else:
            # For general queries, allow more creativity
            config["do_sample"] = True
            config["temperature"] = 0.7
            config["top_p"] = 0.9
            config["top_k"] = 50
            
        return config

    def clean_response(self, prompt: str, full_response: str) -> str:
        """Clean up model response based on model type and formatting."""
        style = self.model_meta["formatting_style"]
        
        # Extract the portion after any assistant marker
        if style == "gemma":
            # Handle the specific format <start_of_turn>model and user tags
            if "<start_of_turn>model" in full_response:
                parts = full_response.split("<start_of_turn>model")
                if len(parts) > 1:
                    response = parts[1].strip()
                    # Remove any trailing end of turn tag
                    response = response.split("<end_of_turn>")[0].strip()
                    # Remove any other Gemma tags
                    response = response.replace("<start_of_turn>user", "").strip()
                    response = response.replace("user", "").strip()
                    response = response.replace("model", "").strip()
                    return response
        elif style == "llama":
            parts = full_response.split("Assistant\n")
            if len(parts) > 1:
                response = parts[1].strip()
                response = response.split("\n")[0].strip()
                return response
        elif style == "phi":
            parts = full_response.split("Assistant: ")
            if len(parts) > 1:
                return parts[1].strip()
        elif style == "deepseek":
            parts = full_response.split("Assistant: ")
            if len(parts) > 1:
                return parts[1].strip()
        
        # Generic cleanup if specific markers not found
        if prompt in full_response:
            response = full_response[len(prompt):].strip()
        else:
            # Try to find where the response begins using common markers
            assistant_markers = ["ASSISTANT:", "Assistant:", "AI:", "Response:", "model"]
            for marker in assistant_markers:
                if marker in full_response:
                    response = full_response.split(marker, 1)[1].strip()
                    break
            else:
                # If no markers found, just take everything
                response = full_response.strip()
        
        # Additional cleanup to remove any remaining model/user markers
        response = re.sub(r'(^|\s)user(\s|$)', ' ', response)
        response = re.sub(r'(^|\s)model(\s|$)', ' ', response)
        
        # Clean up excessive whitespace
        response = re.sub(r'\s+', ' ', response).strip()
                
        return response

    def process_input(self, text: str, max_retries: int = 2) -> str:
        """Process user input and generate a response."""
        start_total = time.time()
        try:
            # Normalize input for caching (strip whitespace)
            text = text.strip()
            if not text:
                return "Please enter a valid query. 😊"

            # Check cache for a response
            if text in self.cache:
                logging.info(f"Cache hit for input: {text}")
                return self.cache[text]

            # Detect query type
            is_math = self.is_math_query(text)
            is_factual = bool(re.search(r'(what|when|where|who|why|how|tell me|explain|define)', text.lower()))
            
            # Initialize result for math queries
            result = None

            # Check if the query is a mathematical expression
            if is_math:
                result = self.extract_and_evaluate_math(text)
                if result is None:
                    return "I'm sorry, I couldn't evaluate the mathematical expression. Please try again with a valid expression. 😔"

            # Format prompt based on model and query type
            prompt = self.format_prompt(text, is_math, result)
            logging.info(f"Formatted prompt: {prompt}")

            # Get optimized generation config
            gen_config = self.optimize_generation_config(is_math, is_factual)

            # Retry loop to improve accuracy
            for attempt in range(max_retries + 1):
                # Tokenize input
                start_tokenize = time.time()
                inputs = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=min(512, self.model_meta["context_length"]),
                    padding=True,
                    add_special_tokens=True
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                logging.info(f"Tokenization took {time.time() - start_tokenize:.2f} seconds")

                # Generate response
                start_generate = time.time()
                with torch.inference_mode():  # Faster than no_grad for inference
                    outputs = self.model.generate(
                        input_ids=inputs["input_ids"],
                        attention_mask=inputs["attention_mask"],
                        max_new_tokens=gen_config["max_new_tokens"],
                        min_length=gen_config["min_length"],
                        num_return_sequences=1,
                        do_sample=gen_config["do_sample"],
                        temperature=gen_config["temperature"],
                        top_p=gen_config["top_p"],
                        top_k=gen_config["top_k"],
                        pad_token_id=self.tokenizer.pad_token_id,
                        repetition_penalty=gen_config["repetition_penalty"],
                        no_repeat_ngram_size=gen_config["no_repeat_ngram_size"]
                    )
                logging.info(f"Generation took {time.time() - start_generate:.2f} seconds")

                # Decode response
                start_decode = time.time()
                full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                logging.info(f"Raw response: {full_response}")

                # Clean response
                response = self.clean_response(prompt, full_response)
                
                # Skip relevance and validation for math queries (already handled)
                if not is_math:
                    # Check relevance and validate response
                    if not self.is_response_relevant(text, response):
                        logging.info(f"Response deemed irrelevant on attempt {attempt + 1}: {response}")
                        if attempt < max_retries:
                            # Reformulate prompt for next attempt
                            prompt = self.format_prompt(f"I need a clear and accurate answer to: {text}")
                            continue
                        return "I'm sorry, I couldn't find an accurate answer to your question. 😔"

                    if not self.validate_response(text, response):
                        logging.info(f"Response failed validation on attempt {attempt + 1}: {response}")
                        if attempt < max_retries:
                            # Add more specific guidance for the next attempt
                            prompt = self.format_prompt(f"I need a specific and factual answer to: {text}")
                            continue
                        return "I'm sorry, I couldn't find an accurate answer to your question. 😔"

                # Remove duplicate code blocks or text
                lines = response.split("\n")
                seen = set()
                cleaned_lines = []
                for line in lines:
                    if line.strip() not in seen:
                        seen.add(line.strip())
                        cleaned_lines.append(line)
                response = "\n".join(cleaned_lines).strip()

                logging.info(f"Cleaned response: {response}")
                logging.info(f"Decoding and cleanup took {time.time() - start_decode:.2f} seconds")

                # Cache the response
                self.cache[text] = response

                logging.info(f"Total processing took {time.time() - start_total:.2f} seconds")
                return response

            return "I'm sorry, I couldn't find an accurate answer to your question after multiple attempts. 😔"

        except Exception as e:
            logging.error(f"Processing error: {e}")
            return f"An error occurred while processing your request. Please try again with a different question."

def main():
    try:
        engine = USBAIEngine()
        print("USB-AI Session Started (Gemma-3-1B-IT). Type 'exit' or 'quit' to end the session.")
        logging.info("Interactive session started")

        while True:
            user_input = input("> ")
            if user_input.lower() in ["exit", "quit"]:
                break

            response = engine.process_input(user_input)
            print(response)
            logging.info(f"User: {user_input}")
            logging.info(f"AI: {response}")

        print("Session ended. Goodbye!")
        logging.info("Interactive session ended")

    except Exception as e:
        logging.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()