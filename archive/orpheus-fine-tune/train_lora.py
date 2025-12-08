from unsloth import FastLanguageModel
import torch
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments, DataCollatorForTokenClassification

MAX_SEQ_LENGTH = 2048 
CHARACTER_NAME = "test_character"
DATASET_PATH = f"../training/{CHARACTER_NAME}/dataset.jsonl"
CHECKPOINTS_DIR = f"../training/{CHARACTER_NAME}/checkpoints"
OUTPUT_DIR = f"../lora_adapters/{CHARACTER_NAME}"

def main():
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = "unsloth/orpheus-3b-0.1-pretrained",
        max_seq_length = MAX_SEQ_LENGTH,
        dtype = None,
        load_in_4bit = False,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r = 64, # The rank of the fine-tuning process -> suggested: 8,16,32,64,128
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj",],
        lora_alpha=64, # scaling factor that controls the strength of the fine-tuned adjustments -> r or 2*r
        lora_dropout = 0.01, # 0 
        bias = "none", 
        use_gradient_checkpointing = True,
        random_state = 3407,
    )
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    print("Starting Training...")
    data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = dataset,
        dataset_text_field = "input_ids",
        max_seq_length = MAX_SEQ_LENGTH,
        packing = False,
        data_collator = data_collator,
        args = TrainingArguments(
            per_device_train_batch_size = 2,
            gradient_accumulation_steps = 4,
            warmup_steps = 15,
            max_steps = 150,
            learning_rate = 3e-4, # 2e-4
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 1,
            optim = "adamw_8bit",
            weight_decay = 0.001,
            lr_scheduler_type = "linear",
            seed = 3407,
            output_dir = CHECKPOINTS_DIR,
            remove_unused_columns=False,
        ),
    )

    trainer.train()
    # note: aim for 2.8-3.5 loss

    print(f"Saving LoRA adapter to {OUTPUT_DIR}")
    model.save_pretrained(OUTPUT_DIR)

if __name__ == "__main__":
    main()
