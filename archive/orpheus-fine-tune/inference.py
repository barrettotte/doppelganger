from unsloth import FastLanguageModel
import torch
from snac import SNAC
import soundfile as sf
import numpy as np

BASE_MODEL = "unsloth/orpheus-3b-0.1-pretrained"
ADAPTER_PATH = "../lora_adapters/test_character"

PROMPT_TEXT = "This is a test to see if the model was trained properly"
# PROMPT_TEXT = "Our Father, who art in heaven, hallowed be thy Name, thy kingdom come, thy will be done, on earth as it is in heaven. Give us this day our daily bread. And forgive us our trespasses, as we forgive those who trespass against us. And lead us not into temptation, but deliver us from evil."
# PROMPT_TEXT = "The FitnessGram Pacer Test is a multistage aerobic capacity test that progressively gets more difficult as it continues. The 20 meter pacer test will begin in 30 seconds. Line up at the start. The running speed starts slowly, but gets faster each minute after you hear this signal. BEEP. A single lap should be completed each time you hear this sound. DING. Remember to run in a straight line, and run as long as possible. The second time you fail to complete a lap before the sound, your test is over. The test will begin on the word start. On your mark, get ready, start."

OUTPUT_WAV = "output.wav"

TOKEN_TO_FIND = 128257
TOKEN_TO_REMOVE = 128258
GLOBAL_OFFSET = 128266

def redistribute_codes(code_list, snac_model):
    """
    Your provided logic to map flattened 7-tuples back to 3 SNAC layers.
    """
    layer_1 = []
    layer_2 = []
    layer_3 = []
    MIN_VAL = 0
    MAX_VAL = 4095
    
    # Iterate in chunks of 7
    for i in range((len(code_list) + 1) // 7):
        if 7*i+6 < len(code_list):
            c1 = code_list[7*i]
            c2_a = code_list[7*i+1] - 4096
            c3_a = code_list[7*i+2] - 8192
            c3_b = code_list[7*i+3] - 12288
            c2_b = code_list[7*i+4] - 16384
            c3_c = code_list[7*i+5] - 20480
            c3_d = code_list[7*i+6] - 24576

            # if LLM predicts slightly wrong token, force it to nearest valid audio code 
            c1 = max(MIN_VAL, min(MAX_VAL, c1))
            c2_a = max(MIN_VAL, min(MAX_VAL, c2_a))
            c2_b = max(MIN_VAL, min(MAX_VAL, c2_b))
            c3_a = max(MIN_VAL, min(MAX_VAL, c3_a))
            c3_b = max(MIN_VAL, min(MAX_VAL, c3_b))
            c3_c = max(MIN_VAL, min(MAX_VAL, c3_c))
            c3_d = max(MIN_VAL, min(MAX_VAL, c3_d))

            layer_1.append(c1)
            layer_2.append(c2_a)
            layer_3.append(c3_a)
            layer_3.append(c3_b)
            layer_2.append(c2_b)
            layer_3.append(c3_c)
            layer_3.append(c3_d)
        
    codes = [
        torch.tensor(layer_1).unsqueeze(0).to("cuda"),
        torch.tensor(layer_2).unsqueeze(0).to("cuda"),
        torch.tensor(layer_3).unsqueeze(0).to("cuda")
    ]
    
    with torch.no_grad():
        audio_hat = snac_model.decode(codes)
    return audio_hat

def main():
    print("Loading Base Model + Adapter...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = BASE_MODEL,
        max_seq_length = 8192, # context window
        dtype = None,
        load_in_4bit = False,
    )
    
    model = FastLanguageModel.for_inference(model)
    model.load_adapter(ADAPTER_PATH)

    print("Loading SNAC decoder...")
    snac_model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").to("cuda")

    txt = f"""Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
Convert this text to speech: {PROMPT_TEXT}

### Response:
"""
    inputs = tokenizer(txt, return_tensors="pt").to("cuda")
    input_ids = inputs.input_ids
    attention_mask = inputs.attention_mask
    
    # append start token manually
    start_token = torch.tensor([[TOKEN_TO_FIND]], device="cuda")
    input_ids = torch.cat([input_ids, start_token], dim=1)

    # extend attention mask for new token
    attention_mask_extension = torch.ones((1, 1), device="cuda")
    attention_mask = torch.cat([attention_mask, attention_mask_extension], dim=1)

    stop_token_ids = [
        tokenizer.eos_token_id, # 128001
        tokenizer.convert_tokens_to_ids("<|eot_id|>") # 128009
    ]
    stop_token_ids = [id for id in stop_token_ids if id is not None]

    print("Generating audio tokens...")
    generated_ids = model.generate(
        input_ids = input_ids,
        attention_mask = attention_mask,
        # min_new_tokens = 250, # generate something at least
        max_new_tokens = 4000, # Approx 100 tokens = 1 second of audio (roughly)
        use_cache = True,
        pad_token_id = tokenizer.eos_token_id,
        eos_token_id=stop_token_ids,
        top_p = 0.9,
        temperature = 0.25, # lower=stable, higher=more expressive/unstable
        repetition_penalty = 1.2, # do not use - audio LLMs generate silence as specific repeated code
        # do_sample = True,
    )

    token_indices = (generated_ids == TOKEN_TO_FIND).nonzero(as_tuple=True)

    if len(token_indices[1]) > 0:
        last_occurrence_idx = token_indices[1][-1].item()
        cropped_tensor = generated_ids[:, last_occurrence_idx+1:]
    else:
        cropped_tensor = generated_ids

    output_tokens = cropped_tensor.squeeze().tolist()
    if not isinstance(output_tokens, list): output_tokens = [output_tokens]
    
    masked_row = [t for t in output_tokens if t != TOKEN_TO_REMOVE and t != tokenizer.eos_token_id]

    # truncate to multiple of 7
    new_length = (len(masked_row) // 7) * 7
    trimmed_row = masked_row[:new_length]

    # remove global Offset
    trimmed_row = [t - GLOBAL_OFFSET for t in trimmed_row]

    if len(trimmed_row) == 0:
        print("No valid audio tokens generated.")
        return

    # attempt to detect and remove audio loop "hum"
    if len(trimmed_row) > 100:
        tail = trimmed_row[-200:]
        if len(set(tail)) < 20:
            print("Detected loop/hum. Trimming...")
            trimmed_row = trimmed_row[:-200]

    print("Decoding SNAC codes...")
    audio_hat = redistribute_codes(trimmed_row, snac_model)
    
    audio_np = audio_hat.squeeze().cpu().numpy()
    sf.write(OUTPUT_WAV, audio_np, 24000)
    print(f"Saved to {OUTPUT_WAV}")

if __name__ == "__main__":
    main()
