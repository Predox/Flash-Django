from __future__ import annotations

from django.conf import settings
from PIL import Image, ImageEnhance, ImageFilter, ImageChops, ImageDraw
import numpy as np
import cv2
import os
from time import perf_counter
from typing import Any
from io import BytesIO
from django.core.files.base import ContentFile
import json
import requests
import time

from .segmentation import run_deeplab_mask, apply_gray_inside_mask
from .models import ProcessedImage, IALog
import replicate
import base64


import os
os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")

try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except Exception:
    HAS_REMBG = False


def _log(image: ProcessedImage, model_name: str, elapsed_ms: int, status: str, message: str = '') -> None:
    IALog.objects.create(
        image=image,
        model_name=model_name,
        elapsed_ms=elapsed_ms,
        status=status,
        message=message,
    )



def apply_basic_edit(processed_img, params):
    # gera imagem editada usando a função preview
    image = apply_basic_edit_preview(processed_img, params)

    original_name = processed_img.original_image.name
    result_name = original_name.replace("originals", "results")

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    processed_img.result_image.save(
        f"edit_{processed_img.id}.png",
        ContentFile(buffer.getvalue()),
        save=True
    )


def apply_basic_edit_preview(processed_img, params):
    from django.core.files.storage import default_storage
    from PIL import Image
    from io import BytesIO

    with processed_img.original_image.open("rb") as f:
        image = Image.open(f).convert("RGB")



    # ----- AJUSTES SIMPLES (Pillow) -----
    image = ImageEnhance.Brightness(image).enhance(1 + params['exposure'] / 100)
    image = ImageEnhance.Contrast(image).enhance(1 + params['contrast'] / 100)
    image = ImageEnhance.Color(image).enhance(1 + params['saturation'] / 100)

    # ----- AJUSTES AVANÇADOS (OpenCV) -----
    # Pillow (RGB) -> OpenCV (BGR)
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # SHARPNESS
    sharp = params['sharpness']
    if sharp != 0:
        strength = sharp / 25
        kernel = np.array([
            [0, -1 * strength, 0],
            [-1 * strength, 1 + 4 * strength, -1 * strength],
            [0, -1 * strength, 0]
        ])
        img_cv = cv2.filter2D(img_cv, -1, kernel)

    # TEXTURE
    texture = params['texture']
    if texture != 0:
        blur = cv2.GaussianBlur(img_cv, (0, 0), 3)
        highpass = cv2.addWeighted(img_cv, 1 + texture / 50, blur, -(texture / 50), 0)
        img_cv = highpass

    img_np = img_cv.astype(np.float32)

    # SHADOWS – clareia áreas escuras de forma proporcional
    sh = params['shadows'] / 100
    if sh != 0:
        img_np = img_np + ((255 - img_np) * sh)

    # HIGHLIGHTS – escurece áreas muito claras para recuperar detalhes
    hi = params['highlights'] / 100
    if hi != 0:
        img_np = img_np * (1 - hi)

    # WHITES – afeta apenas tons realmente claros
    wh = params['whites'] / 100
    if wh != 0:
        img_np = img_np + (wh * (img_np > 200) * (255 - img_np))

    # BLACKS – afeta apenas tons muito escuros
    bl = params['blacks'] / 100
    if bl != 0:
        img_np = img_np - (bl * (img_np < 50) * img_np)

    # Finalização segura
    img_np = np.clip(img_np, 0, 255).astype("uint8")

    # BGR -> RGB ANTES de voltar pro Pillow
    img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)

    image = Image.fromarray(img_rgb)

    # DESFOQUE DE FUNDO
    blur_amount = params.get("background_blur", 0)

    if blur_amount > 0:
        # converter para OpenCV
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        mask = np.zeros(img_cv.shape[:2], np.uint8)

        # bounding box do assunto
        h, w = img_cv.shape[:2]
        rect = (10, 10, w - 20, h - 20)

        bgModel = np.zeros((1,65), np.float64)
        fgModel = np.zeros((1,65), np.float64)

        cv2.grabCut(img_cv, mask, rect, bgModel, fgModel, 5, cv2.GC_INIT_WITH_RECT)

        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")

        # fundo borrado
        blur_strength = max(1, int(blur_amount / 10) * 3)
        blurred = cv2.GaussianBlur(img_cv, (blur_strength|1, blur_strength|1), 0)

        # combina bordas
        img_cv = blurred * (1 - mask2[:, :, None]) + img_cv * mask2[:, :, None]

        image = Image.fromarray(cv2.cvtColor(img_cv.astype("uint8"), cv2.COLOR_BGR2RGB))


    return image




def remove_background(image_obj: ProcessedImage) -> None:
    start = perf_counter()
    try:
        if not HAS_REMBG:
            raise RuntimeError('rembg não está instalado. Use: pip install rembg')

        field = image_obj.result_image if image_obj.result_image else image_obj.original_image
        with field.open("rb") as f:
            input_bytes = f.read()

        output_bytes = rembg_remove(input_bytes)

        file_name = f'remove_bg_{image_obj.id}.png'
        image_obj.result_image.save(file_name, ContentFile(output_bytes), save=True)

        elapsed = int((perf_counter() - start) * 1000)
        _log(image_obj, 'rembg_remove_bg', elapsed, 'success')
    except Exception as exc:
        elapsed = int((perf_counter() - start) * 1000)
        _log(image_obj, 'rembg_remove_bg', elapsed, 'error', str(exc))
        raise



def inpainting(image_obj: ProcessedImage, prompt: str | None = None) -> None:
    """Stub para inpainting.
    Aqui você pode integrar um modelo de difusão (como Stable Diffusion) no futuro.
    Por enquanto, apenas copia a imagem original para o resultado.
    """
    start = perf_counter()
    try:
        with image_obj.original_image.open("rb") as f:
            img = Image.open(f).convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        file_name = f'inpainting_{image_obj.id}.png'
        image_obj.result_image.save(file_name, ContentFile(buffer.getvalue()), save=True)

        elapsed = int((perf_counter() - start) * 1000)
        msg = f'Inpainting stub executado. Prompt: {prompt!r}'
        _log(image_obj, 'inpainting_stub', elapsed, 'success', msg)
    except Exception as exc:
        elapsed = int((perf_counter() - start) * 1000)
        _log(image_obj, 'inpainting_stub', elapsed, 'error', str(exc))
        raise



def apply_deeplab(processed_image: "ProcessedImage"):
    import tensorflow as tf
    import os
    from django.conf import settings
    import numpy as np
    from PIL import Image, ImageChops, ImageDraw

    model_path = os.path.join(
        settings.BASE_DIR,
        "editor",
        "ai_models",
        "deeplab_v3_257_mv_gpu.tflite"
    )

    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    """
    Usa o DeepLab apenas para melhorar o contorno da seleção.
    NÃO aplica preto e branco, NÃO altera a imagem original.
    """

    # -------------------------
    # 1. Carrega imagem original
    # -------------------------
    with processed_image.original_image.open("rb") as f:
        img = Image.open(f).convert("RGB")
    w, h = img.size

    # -------------------------
    # 2. Lê seleção salva no banco
    # -------------------------
    selections = json.loads(processed_image.selections)

    sel = selections[0]
    if "path" not in sel or len(sel["path"]) < 3:
        raise ValueError("Seleção inválida: faltando path.")

    polygon = [(p["x"], p["y"]) for p in sel["path"]]

    # -------------------------
    # 3. Máscara do usuário
    # -------------------------
    user_mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(user_mask)
    draw.polygon(polygon, fill=255)

    # -------------------------
    # 4. Preparação DeepLab
    # -------------------------
    target_size = (257, 257)
    img_resized = img.resize(target_size)

    inp = np.array(img_resized, dtype=np.float32)
    inp = inp[np.newaxis, ...] / 255.0

    start = perf_counter()
    DEEP_LAB.set_tensor(input_details[0]["index"], inp)
    DEEP_LAB.invoke()

    output = DEEP_LAB.get_tensor(output_details[0]['index'])[0]
    segmap = np.argmax(output, axis=-1).astype(np.uint8)
    elapsed = int((perf_counter() - start) * 1000)

    # -------------------------
    # 5. Redimensiona máscara IA
    # -------------------------
    segmap_img = Image.fromarray(segmap).resize((w, h), Image.NEAREST)

    PERSON_CLASS = 15
    ai_mask = segmap_img.point(lambda p: 255 if p == PERSON_CLASS else 0)

    # IA só refina dentro da seleção do usuário
    combined_mask = ImageChops.multiply(ai_mask, user_mask)

    # -------------------------
    # 6. NÃO aplica PB e NÃO salva imagem editada
    # -------------------------
    # ANTES: criava img_gray e fazia composite → removido!

    # -------------------------
    # 7. Apenas extrair polígono refinado
    # -------------------------
    refined_polygon = mask_to_polygon(combined_mask)

    # Log IA
    _log(processed_image, "deeplab_v3_refine", elapsed, "success")

    return refined_polygon


def mask_to_polygon(mask):
    """Extrai o maior contorno da máscara como polígono."""
    mask_np = np.array(mask)

    # Threshold para garantir binário
    _, thresh = cv2.threshold(mask_np, 1, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # pega maior contorno
    largest = max(contours, key=cv2.contourArea)

    epsilon = 0.0015 * cv2.arcLength(largest, True)

    approx = cv2.approxPolyDP(
        largest,
        epsilon,
        True
    )


    # converte para lista de dicionários
    polygon = [{"x": int(p[0][0]), "y": int(p[0][1])} for p in approx]

    return polygon


def call_inpainting_model(selected_region, mask, prompt, request):
    import replicate
    from io import BytesIO
    import base64
    from PIL import Image
    import numpy as np
    
    print("Usando timothybrooks/instruct-pix2pix:", prompt)

    # -------- 1) Converter região selecionada para PNG base64 --------
    buf = BytesIO()
    selected_region.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    print("📏 IMG BASE64 LEN:", len(base64.b64encode(image_bytes)))

    # Criar string base64 no formato esperado
    encoded_img = "data:image/png;base64," + base64.b64encode(image_bytes).decode()

    # -------- 2) Chamar o modelo --------
    output = replicate.run(
        "timothybrooks/instruct-pix2pix:30c1d0b916a6f8efce20493f5d61ee27491ab2a60437c13c588468b9810ec23f",
        input={
            "image": encoded_img,
            "prompt": prompt
        }
    )

    # O output é uma lista contendo arquivos
    result_url = output[0]

    print("🌐 RESULT URL:", result_url)

    # -------- 3) Baixar imagem gerada --------
    import requests
    img_bytes = requests.get(result_url).content
    edited_region = Image.open(BytesIO(img_bytes)).convert("RGBA")

    # -------- 4) Redimensionar imagem editada para o tamanho original da seleção --------
    edited_region = edited_region.resize(selected_region.size)

    return edited_region

def call_pix2pix_full(image: Image.Image, prompt: str):
    import replicate
    import requests
    import base64
    from io import BytesIO

    print("MODO FULL → Instruct-Pix2Pix")

    buf = BytesIO()
    image.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    output = replicate.run(
        "timothybrooks/instruct-pix2pix:30c1d0b916a6f8efce20493f5d61ee27491ab2a60437c13c588468b9810ec23f",
        input={
            "image": f"data:image/png;base64,{img_b64}",
            "prompt": prompt
        }
    )

    url = output[0]
    img_bytes = requests.get(url).content
    return Image.open(BytesIO(img_bytes))




def apply_edit_with_prompt(request, processed_image, selection_polygon, prompt):
    from PIL import ImageDraw
    import os
    from io import BytesIO

    print("apply_edit_with_prompt executando…")

    mode = request.POST.get("edit_mode", "local")
    print("🔧 MODO:", mode)

    # Carrega imagem original
    with processed_image.current_image_field().open("rb") as f:
        image = Image.open(f).convert("RGBA")
    w, h = image.size

    # Se for FULL → ignora seleção e chama Pix2Pix
    if mode == "full":
        edited = call_pix2pix_full(image, prompt)

        buffer = BytesIO()
        edited.save(buffer, format="PNG")

        filename = f"results/edit_{processed_image.id}.png"
        processed_image.result_image.save(
            f"edit_{processed_image.id}.png",
            ContentFile(buffer.getvalue()),
            save=True
        )

        return processed_image.result_image.url


    # MODO LOCAL (SELEÇÃO) — seu fluxo original
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)

        # ------------------------------
    # NORMALIZAR SELEÇÃO
    # ------------------------------
    print("DEBUG recebida seleção:", selection_polygon)

    # 1) Se vier string JSON → decodifica
    if isinstance(selection_polygon, str):
        selection_polygon = json.loads(selection_polygon)

    # 2) Se vier como lista externa
    if isinstance(selection_polygon, list):
        # pode ser: [{"path":[...]}]
        if len(selection_polygon) > 0 and isinstance(selection_polygon[0], dict) and "path" in selection_polygon[0]:
            selection_polygon = selection_polygon[0]["path"]

    # 3) Se vier como dict externo: {"path":[...]}
    if isinstance(selection_polygon, dict) and "path" in selection_polygon:
        selection_polygon = selection_polygon["path"]

    # 4) SELEÇÃO DEVE SER lista de pontos
    if not isinstance(selection_polygon, list):
        raise ValueError(f"Seleção inválida após normalização: {selection_polygon}")

    # 5) Converte pontos
    poly_points = [(p["x"], p["y"]) for p in selection_polygon]

    draw.polygon(poly_points, fill=255)

    selected_region = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    selected_region.paste(image, mask=mask)

    edited_region = call_inpainting_model(selected_region, mask, prompt, request)

    final_img = image.copy()
    final_img.paste(edited_region, mask=mask)

    buffer = BytesIO()
    final_img.save(buffer, format="PNG")

    processed_image.result_image.save(
        f"edit_{processed_image.id}.png",
        ContentFile(buffer.getvalue()),
        save=True
    )
    return processed_image.result_image.url
