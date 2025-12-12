
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    # fallback se você usar tensorflow em vez de tflite-runtime
    from tensorflow import lite as tflite


# Caminho do modelo
MODEL_PATH = Path(__file__).resolve().parent / "models" / "deeplab_v3.tflite"

_interpreter = None
_input_details = None
_output_details = None


def _load_interpreter():
    """Carrega o modelo DeepLab V3 na primeira vez."""
    global _interpreter, _input_details, _output_details
    if _interpreter is not None:
        return

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modelo DeepLab não encontrado em {MODEL_PATH}")

    _interpreter = tflite.Interpreter(model_path=str(MODEL_PATH))
    _interpreter.allocate_tensors()
    _input_details = _interpreter.get_input_details()
    _output_details = _interpreter.get_output_details()


def _prepare_input(image: Image.Image) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    Redimensiona a imagem para o tamanho de entrada do modelo e normaliza.
    Retorna o array pronto e o (w, h) original.
    """
    orig_w, orig_h = image.size
    input_shape = _input_details[0]["shape"]
    in_h, in_w = int(input_shape[1]), int(input_shape[2])

    img_resized = image.convert("RGB").resize((in_w, in_h), Image.BILINEAR)
    arr = np.asarray(img_resized, dtype=np.float32)

    arr = arr / 255.0

    arr = np.expand_dims(arr, axis=0).astype(_input_details[0]["dtype"])
    return arr, (orig_w, orig_h)


def run_deeplab_mask(image: Image.Image) -> Image.Image:
    """
    Roda o DeepLab V3 na imagem e devolve uma máscara em escala de cinza (PIL 'L'):
    - 255 = objeto (qualquer classe != 0)
    - 0   = background
    """
    _load_interpreter()

    input_data, (orig_w, orig_h) = _prepare_input(image)

    _interpreter.set_tensor(_input_details[0]["index"], input_data)
    _interpreter.invoke()

    output_data = _interpreter.get_tensor(_output_details[0]["index"])
    logits = output_data[0]
    label_map = logits.argmax(axis=-1).astype(np.uint8)

    fg = (label_map != 0).astype(np.uint8) * 255

    mask_small = Image.fromarray(fg, mode="L")
    mask = mask_small.resize((orig_w, orig_h), Image.NEAREST)
    return mask


def apply_gray_inside_mask(image: Image.Image, mask: Image.Image) -> Image.Image:
    """
    Deixa a área da máscara em preto e branco (saturação 0),
    mantendo o resto colorido.
    """
    from PIL import ImageOps

    image_rgb = image.convert("RGB")
    gray = ImageOps.grayscale(image_rgb).convert("RGB")

    result = Image.composite(gray, image_rgb, mask)
    return result
