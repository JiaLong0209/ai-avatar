import os
import torch
from torch import no_grad, LongTensor
import argparse
import commons
import utils
from models import SynthesizerTrn
import soundfile as sf
from text import text_to_sequence
from deep_translator import GoogleTranslator

# --- Centralized Language Definitions ---
# This dictionary is the single source of truth for language information.
# Keys are the user-facing command-line arguments (e.g., "JA").
LANGUAGES = {
    "JA": {"name": "日本語", "mark": "[JA]", "code": "ja"},
    "ZH": {"name": "简体中文", "mark": "[ZH]", "code": "zh-CN"},
    "EN": {"name": "English", "mark": "[EN]", "code": "en"},
}

# --- Helper Functions ---
def get_text(text: str, hps) -> LongTensor:
    """Converts raw text to a sequence of token IDs."""
    text_norm = text_to_sequence(text, hps.symbols, hps.data.text_cleaners)
    if hps.data.add_blank:
        text_norm = commons.intersperse(text_norm, 0)
    text_norm = LongTensor(text_norm)
    return text_norm

# --- Main Execution ---
def main():
    """
    Main function to run the Text-to-Speech command-line interface with translation.
    """
    # --- Argument Parsing ---
    # Use the keys from our LANGUAGES dictionary as the choices
    lang_choices = list(LANGUAGES.keys())
    
    parser = argparse.ArgumentParser(
        description="Command-line interface for VITS Text-to-Speech with auto-translation"
    )
    parser.add_argument("-t", "--text", type=str, required=True, help="Text to synthesize.")
    parser.add_argument("-s", "--speaker", type=str, required=True, help="Speaker's name (must exist in config).")
    parser.add_argument("-l", "--language", choices=lang_choices, default="ZH", help=f"TARGET language for the speech output. Choices: {lang_choices}")
    parser.add_argument("--source_language", choices=["auto"] + lang_choices, default="auto", help=f"SOURCE language of the input text. 'auto' enables detection. Choices: {['auto'] + lang_choices}")
    parser.add_argument("-o", "--output", type=str, default="output.wav", help="Path to save the output audio file.")
    parser.add_argument("--model_dir", type=str, default="G_latest.pth", help="Path to the model file.")
    parser.add_argument("--config_dir", type=str, default="config.json", help="Path to the config file.")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed. Larger is slower.")
    args = parser.parse_args()

    # --- Device Setup ---
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # --- Translation Logic ---
    processed_text = args.text
    source_lang_key = args.source_language
    target_lang_key = args.language

    try:
        # 1. Detect source language if set to 'auto'
        if source_lang_key == 'auto':
            detected_code = GoogleTranslator().detect(args.text)[0]
            # Find the key (e.g., "ZH") matching the detected code
            for key, info in LANGUAGES.items():
                if info["code"] == detected_code:
                    source_lang_key = key
                    break
            print(f"Detected source language: {source_lang_key}")

        # 2. Translate if source and target languages are different
        if source_lang_key and source_lang_key != "auto" and source_lang_key != target_lang_key:
            source_info = LANGUAGES[source_lang_key]
            target_info = LANGUAGES[target_lang_key]
            print(f"Translating from {source_info['name']} ({source_lang_key}) to {target_info['name']} ({target_lang_key})...")
            
            translator = GoogleTranslator(source=source_info['code'], target=target_info['code'])
            processed_text = translator.translate(args.text)
            print(f"Translated text: {processed_text}")
        else:
            print("Source and target languages are the same, no translation needed.")

    except Exception as e:
        print(f"Warning: Translation failed with error: {e}. Using original text.")
        processed_text = args.text

    # --- Load Model and Config ---
    print("\nLoading model...")
    hps = utils.get_hparams_from_file(args.config_dir)
    
    if args.speaker not in hps.speakers:
        print(f"Error: Speaker '{args.speaker}' not found in the model config.")
        print(f"Available speakers are: {list(hps.speakers.keys())}")
        return

    speaker_id = hps.speakers[args.speaker]
    
    net_g = SynthesizerTrn(
        len(hps.symbols),
        hps.data.filter_length // 2 + 1,
        hps.train.segment_size // hps.data.hop_length,
        n_speakers=hps.data.n_speakers,
        **hps.model
    ).to(device)
    
    _ = net_g.eval()
    _ = utils.load_checkpoint(args.model_dir, net_g, None)
    print("Model loaded successfully.")

    # --- Text Preprocessing ---
    target_lang_info = LANGUAGES[target_lang_key]
    text_to_synth = target_lang_info["mark"] + processed_text + target_lang_info["mark"]
    stn_tst = get_text(text_to_synth, hps)

    # --- Inference ---
    print(f"Synthesizing speech for: '{processed_text}'...")
    with no_grad():
        x_tst = stn_tst.unsqueeze(0).to(device)
        x_tst_lengths = LongTensor([stn_tst.size(0)]).to(device)
        sid = LongTensor([speaker_id]).to(device)
        
        audio = net_g.infer(
            x_tst, 
            x_tst_lengths, 
            sid=sid, 
            noise_scale=.667, 
            noise_scale_w=0.8, 
            length_scale=1.0 / args.speed
        )[0][0, 0].data.cpu().float().numpy()

    # --- Save Audio ---
    sampling_rate = hps.data.sampling_rate
    sf.write(args.output, audio, sampling_rate)
    print(f"\nSuccessfully generated audio and saved to: {args.output}")


if __name__ == "__main__":
    main()