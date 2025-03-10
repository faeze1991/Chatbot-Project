# -*- coding: utf-8 -*-
"""final_version2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1xrydWh7IXtlZICBsmsMXXRsZlJbYWsvZ
"""

!kill -9 -1

!pip install -q transformers einops accelerate langchain bitsandbytes

!huggingface-cli login

!huggingface-cli whoami

pip install peft

!pip install transformers datasets accelerate bitsandbytes
!pip install torch --index-url https://download.pytorch.org/whl/cu118  # Ensure CUDA compatibility

from huggingface_hub import HfApi

api = HfApi()
models = api.list_models(author="meta-llama")
for model in models:
    print(model.modelId)

from transformers import AutoModelForCausalLM, AutoTokenizer

# Define model name
model_name = "meta-llama/Llama-3.1-8B-Instruct"

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=True)

# Load model (might take time)
model = AutoModelForCausalLM.from_pretrained(model_name, use_auth_token=True)

from google.colab import drive

# ✅ Mount Google Drive
drive.mount('/content/drive')

# ✅ Define Save Path
SAVE_PATH = "/content/drive/MyDrive/llama-sparql-full"

# ✅ Ensure the directory exists
import os
os.makedirs(SAVE_PATH, exist_ok=True)

# ✅ Save Full Model & Tokenizer
model.save_pretrained(SAVE_PATH)
tokenizer.save_pretrained(SAVE_PATH)

print(f"✅ Full model saved permanently at: {SAVE_PATH}")

input_text = "Convert the question 'Where is the Eiffel Tower?' into a SPARQL query."

# Tokenize input
inputs = tokenizer(input_text, return_tensors="pt")

# Generate output
output = model.generate(**inputs, max_length=150)

# Decode output
generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
print("Generated Output:", generated_text)

#finetune the model on the dataset

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, BitsAndBytesConfig
from datasets import load_dataset, Dataset
import pandas as pd

# ✅ Load LC-QuAD dataset
df = pd.read_json("test-data.json")
df = df.dropna(subset=["corrected_question", "sparql_query"])  # Remove incomplete data

# ✅ Convert to Hugging Face dataset format
dataset = Dataset.from_pandas(df)

# ✅ Load LLaMA tokenizer
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"  # Change if needed
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_auth_token=True)

# 🔹 Fix: Set Padding Token (LLaMA models don’t have it by default)
tokenizer.pad_token = tokenizer.eos_token  # Use eos_token as padding

# ✅ Tokenization function (Fix)
def preprocess(example):
    model_inputs = tokenizer(
        example["corrected_question"],
        padding="max_length",  # Ensures consistent padding
        truncation=True,
        max_length=256
    )

    labels = tokenizer(
        example["sparql_query"],
        padding="max_length",  # Ensures consistent padding
        truncation=True,
        max_length=256  # Make sure it matches input length!
    )

    model_inputs["labels"] = labels["input_ids"]  # Assign correct labels

    return model_inputs


# ✅ Tokenize dataset
tokenized_dataset = dataset.map(preprocess, batched=True)

# ✅ Split into train and validation
train_test_split = tokenized_dataset.train_test_split(test_size=0.1)
train_dataset = train_test_split["train"]
eval_dataset = train_test_split["test"]

print("✅ Tokenization completed successfully!")

# -----------------------------------------
# ✅ APPLY 4-BIT QUANTIZATION + LoRA FOR TRAINING
# -----------------------------------------
from peft import LoraConfig, get_peft_model
from transformers import BitsAndBytesConfig

# ✅ Define 4-bit Quantization Config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,  # ✅ Load in 4-bit mode (Reduces memory usage by ~75%)
    bnb_4bit_compute_dtype=torch.float16,  # ✅ Use float16 for efficiency
    bnb_4bit_use_double_quant=True,  # ✅ Further memory optimization
)

# ✅ Load Model with 4-bit Quantization
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,  # ✅ Apply 4-bit Quantization
    use_auth_token=True,
    device_map="auto"  # ✅ Automatically assigns model layers to CPU/GPU
)

print("✅ Model successfully loaded in 4-bit mode!")

# ✅ Define LoRA Configuration
lora_config = LoraConfig(
    r=8,  # Rank of adaptation matrix
    lora_alpha=32,
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM"
)

# ✅ Apply LoRA to Model
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

print("✅ LoRA adapters added, model is ready for fine-tuning!")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model

# ✅ Define Model Name
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"  # Change if needed

# ✅ Enable 4-bit Quantization to Reduce Memory Usage
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,  # ✅ Load in 4-bit mode
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

# ✅ Load Model with 4-bit Quantization
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,  # ✅ Apply 4-bit Quantization
    use_auth_token=True,
    device_map="auto"  # ✅ Automatically assigns model layers to CPU/GPU
)

print("✅ Model successfully loaded in 4-bit mode!")

# -----------------------------------------
# ✅ APPLY LoRA ADAPTERS TO ENABLE TRAINING
# -----------------------------------------
lora_config = LoraConfig(
    r=8,  # ✅ Rank of adaptation matrix
    lora_alpha=32,
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM"
)

# ✅ Attach LoRA adapters to the model
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

print("✅ LoRA adapters added, model is ready for fine-tuning!")

training_args = TrainingArguments(
    output_dir="./llama-sparql-finetuned",
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_steps=50,
    per_device_train_batch_size=1,  # 🔹 Reduce batch size further
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=3e-5,
    num_train_epochs=3,
    weight_decay=0.01,
    fp16=True,
    push_to_hub=False
)

# ✅ Initialize Trainer with LoRA Model
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

# ✅ Start fine-tuning
trainer.train()

# ✅ Save the fine-tuned model
model.save_pretrained("./llama-sparql-finetuned")
tokenizer.save_pretrained("./llama-sparql-finetuned")

print("✅ Fine-tuning completed! Model saved.")

#save the model

from google.colab import drive
import os

# ✅ Mount Google Drive
drive.mount('/content/drive')

# ✅ Define the path to save the model in Google Drive
GDRIVE_MODEL_PATH = "/content/drive/My Drive/llama-sparql-finetuned"

# ✅ Ensure the directory exists
os.makedirs(GDRIVE_MODEL_PATH, exist_ok=True)

# ✅ Save fine-tuned model and tokenizer
model.save_pretrained(GDRIVE_MODEL_PATH)
tokenizer.save_pretrained(GDRIVE_MODEL_PATH)

print("✅ Model saved permanently in Google Drive at:", GDRIVE_MODEL_PATH)

from google.colab import drive
drive.mount('/content/drive')

import os

MODEL_PATH = "/content/drive/MyDrive/llama-sparql-full"
print(os.listdir(MODEL_PATH))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# ✅ Correct Path to Google Drive
MODEL_PATH = "/content/drive/MyDrive/llama-sparql-full"

# ✅ Load Tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

# ✅ Load Model Properly (Supports SafeTensors)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.float16,  # Optimized for memory
    device_map="auto"  # Auto-assign to GPU if available
)

print("✅ Fine-tuned model loaded successfully!")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# ✅ Define paths
BASE_MODEL_PATH = "/content/drive/MyDrive/llama-sparql-full"  # Base LLaMA model
FINETUNED_MODEL_PATH = "/content/drive/MyDrive/llama-sparql-finetuned"  # Fine-tuned adapters

# ✅ Load Tokenizer
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH, local_files_only=True)

# ✅ Load Base Model Efficiently
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL_PATH,
    local_files_only=True,  # Force local loading
    torch_dtype=torch.float16,
    device_map="auto"
)

# ✅ Load Fine-Tuned Adapters (LoRA)
model = PeftModel.from_pretrained(model, FINETUNED_MODEL_PATH)

print("✅ Base model + fine-tuned adapters loaded successfully!")

# ✅ Check if tokenizer is loaded
print("Tokenizer:", tokenizer if 'tokenizer' in globals() else "❌ Tokenizer not loaded!")

# ✅ Check model device
print("Model is running on:", model.device)

# ✅ Ensure special tokens are set
if tokenizer.pad_token_id is None:
    tokenizer.pad_token = tokenizer.eos_token  # Use EOS token as padding

print("Pad Token ID:", tokenizer.pad_token_id)



