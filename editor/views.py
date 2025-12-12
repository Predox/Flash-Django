import json
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw
from django.shortcuts import redirect
from django.core.files.storage import default_storage
import base64
import io
from . import services
from editor.models import ProcessedImage
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import base64
from editor.models import Profile
from io import BytesIO
import os
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from .models import ProcessedImage
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404


from .forms import ImageUploadForm, PresetForm
from .models import Preset, ProcessedImage
from . import services


@login_required
def profile_view(request):
    images = request.user.images.order_by('-created_at')[:20]
    total_images = request.user.images.count()
    context = {
        'images': images,
        'total_images': total_images,
    }
    return render(request, 'editor/profile.html', context)


@login_required
def update_profile(request):
    user = request.user

    # garante que o Profile exista
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == "POST":
        name = request.POST.get("name")
        photo = request.FILES.get("photo")

        if name:
            profile.display_name = name
            user.first_name = name  # opcional
            user.save()

        if photo:
            profile.profile_photo = photo

        profile.save()

    return redirect("editor:profile")


@require_GET
@login_required
def load_preset(request, preset_id):
    preset = get_object_or_404(Preset, id=preset_id, user=request.user)

    data = {
        "id": preset.id,
        "name": preset.name,
        "params": {
            "exposure": preset.exposure,
            "contrast": preset.contrast,
            "highlights": preset.highlights,
            "shadows": preset.shadows,
            "whites": preset.whites,
            "blacks": preset.blacks,
            "saturation": preset.saturation,
            "texture": preset.texture,
            "background_blur": preset.background_blur,
            "sharpness": preset.sharpness,
        }
    }
    return JsonResponse(data)



@login_required
def editor_view(request):
    presets = request.user.presets.all()
    upload_form = ImageUploadForm()
    preset_form = PresetForm()

    if request.method == 'POST':
        if request.FILES.get('original_image'):
            upload_form = ImageUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                img = upload_form.save(commit=False)
                img.user = request.user
                img.operation = 'basic_edit'
                img.save()

                request.session['last_image_id'] = img.id
                messages.success(request, 'Imagem importada!')
                return redirect('editor:editor')
            else:
                print("ERRO FORM:", upload_form.errors)



        if "save_preset" in request.POST:
            name = request.POST.get("name")
            last_image_id = request.session.get("last_image_id")
            img = ProcessedImage.objects.filter(id=last_image_id, user=request.user).first()

            if not img or not img.params:
                messages.error(request, "Nenhum ajuste para salvar.")
                return redirect("editor:editor")

            preset = Preset.objects.create(
                user=request.user,
                name=name,
                exposure=img.params.get("exposure", 0),
                contrast=img.params.get("contrast", 0),
                saturation=img.params.get("saturation", 0),
                sharpness=img.params.get("sharpness", 0),
                texture=img.params.get("texture", 0),
                highlights=img.params.get("highlights", 0),
                shadows=img.params.get("shadows", 0),
                whites=img.params.get("whites", 0),
                blacks=img.params.get("blacks", 0),
                background_blur=img.params.get("background_blur", 0),
            )

            messages.success(request, "Preset salvo com sucesso.")
            return redirect("editor:editor")



        if 'apply_basic' in request.POST:
            image_id = request.POST.get('image_id')
            img = get_object_or_404(ProcessedImage, id=image_id, user=request.user)

            params = {
                'exposure': float(request.POST.get('exposure', 0)),
                'contrast': float(request.POST.get('contrast', 0)),
                'saturation': float(request.POST.get('saturation', 0)),
                'sharpness': float(request.POST.get('sharpness', 0)),
                'texture': float(request.POST.get('texture', 0)),
                'highlights': float(request.POST.get('highlights', 0)),
                'shadows': float(request.POST.get('shadows', 0)),
                'whites': float(request.POST.get('whites', 0)),
                'blacks': float(request.POST.get('blacks', 0)),
            }

            services.apply_basic_edit(img, params)

            img.operation = 'basic_edit'
            img.params = params
            img.save()

            # Atualiza preview
            request.session['last_image_id'] = img.id

            messages.success(request, 'Ajustes avançados aplicados.')
            return redirect('editor:editor')


    last_image = None  # Começa vazio

    # se acabou de fazer upload, mostramos:
    if 'last_image_id' in request.session:
        last_image = ProcessedImage.objects.filter(
            id=request.session.get('last_image_id'),
            user=request.user
        ).first()

    context = {
        'presets': presets,
        'upload_form': upload_form,
        'preset_form': preset_form,
        'last_image': last_image,
    }
    return render(request, 'editor/editor.html', context)

@login_required
def editor_open_image(request, image_id):
    img = get_object_or_404(ProcessedImage, id=image_id, user=request.user)

    # Salva para o editor abrir automaticamente
    request.session['last_image_id'] = img.id

    return redirect("editor:editor")


@login_required
def remove_bg_view(request, image_id):
    img = get_object_or_404(ProcessedImage, id=image_id, user=request.user)
    try:
        services.remove_background(img)
        img.operation = 'remove_bg'
        img.save()
        messages.success(request, 'Fundo removido com IA.')
    except Exception as exc:
        messages.error(request, f'Erro ao remover fundo: {exc}')
    return redirect('editor:editor')

@login_required
@csrf_exempt
def remove_bg_live(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método inválido"}, status=400)

    image_id = request.POST.get("image_id")
    img = get_object_or_404(ProcessedImage, pk=image_id, user=request.user)

    uploaded = request.FILES.get("edited_image")
    if not uploaded:
        return JsonResponse({"error": "imagem não enviada"}, status=400)

    # sobrescreve a imagem base da edição
    img.original_image.save(
        f"live_{img.id}.png",
        uploaded,
        save=True
    )

    # aplica remove bg em cima da imagem EDITADA
    services.remove_background(img)

    img.operation = "remove_bg"
    img.save(update_fields=["operation"])

    return JsonResponse({
        "status": "ok",
        "image_url": img.result_image.url,
        "image_id": img.id
    })




def undo_remove_bg(request, image_id):
    img = get_object_or_404(ProcessedImage, id=image_id, user=request.user)

    # se tiver uma imagem de resultado
    if img.result_image:
        # deletar arquivo físico
        file_path = img.result_image.path if img.result_image else img.original_image.path

        if os.path.exists(file_path):
            os.remove(file_path)

        # limpar campo
        img.result_image = None
        img.save()

    return redirect("editor:editor_with_image", image_id)


@login_required
def ai_selection_view(request, image_id):
    img = get_object_or_404(ProcessedImage, id=image_id, user=request.user)

    if request.method == 'POST':
        # salvar seleção primeiro
        sel_json = request.POST.get("selections_json")
        if sel_json:
            img.selections = sel_json
            img.save()

        # depois trata prompt / IA
        prompt = request.POST.get('prompt') or ''
        try:
            services.inpainting(img, prompt)
            img.operation = 'inpainting'
            img.save()
            messages.success(request, 'Inpainting executado (stub).')
        except Exception as exc:
            messages.error(request, f'Erro ao executar inpainting: {exc}')

        return redirect('editor:editor')

    return render(request, 'editor/ai_selection.html', {'image': img})




@require_POST
@login_required
def delete_preset_ajax(request, preset_id):
    preset = get_object_or_404(Preset, id=preset_id, user=request.user)
    preset.delete()
    return JsonResponse({"status": "ok"})



@login_required
def ajax_apply_edit(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método inválido"}, status=400)

    image_id = request.POST.get("image_id")
    img = get_object_or_404(ProcessedImage, id=image_id, user=request.user)

    params = {
        'exposure': float(request.POST.get('exposure', 0)),
        'contrast': float(request.POST.get('contrast', 0)),
        'saturation': float(request.POST.get('saturation', 0)),
        'sharpness': float(request.POST.get('sharpness', 0)),
        'texture': float(request.POST.get('texture', 0)),
        'highlights': float(request.POST.get('highlights', 0)),
        'shadows': float(request.POST.get('shadows', 0)),
        'whites': float(request.POST.get('whites', 0)),
        'blacks': float(request.POST.get('blacks', 0)),
        'background_blur': float(request.POST.get('background_blur', 0)),
    }

    # 1) Gera a imagem editada (Pillow) em memória
       # salva os parâmetros no modelo para persistirem na UI
    img.params = params
    img.save(update_fields=["params"])

    # Processa preview
    edited_img = services.apply_basic_edit_preview(img, params)

    # Salvar sempre como edited_<id>.png
    result_name = f"results/edited_{img.id}.png"
    result_path = os.path.join(settings.MEDIA_ROOT, result_name)

    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    edited_img.save(result_path)

    # Atualiza o model
    img.result_image.name = result_name
    img.params = params
    img.operation = "basic_edit"
    img.save()


    # 4) Devolve base64 pro preview instantâneo
    buffer = BytesIO()
    edited_img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return JsonResponse({"image": encoded})



def run_ai_inpainting(prompt, b64_img, b64_mask):
    """Simulação temporária — substitua pela API final."""
    print("📌 IA chamada com prompt:", prompt)
    print("Imagem e máscara recebidas!")
    # Aqui você chamará a API real
    return None

@login_required
def deeplab_test_view(request, image_id):
    img = get_object_or_404(ProcessedImage, id=image_id, user=request.user)

    try:
        services.apply_deeplab(img)
        messages.success(request, "DeepLab aplicado com sucesso!")
    except Exception as exc:
        messages.error(request, f"Erro ao aplicar DeepLab: {exc}")

    return redirect("editor:ai_selection", image_id=image_id)

@login_required
def apply_deeplab_ajax(request, image_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método inválido"}, status=400)

    img = get_object_or_404(ProcessedImage, id=image_id, user=request.user)
    selections_json = request.POST.get("selections") 

    if not selections_json:
        return JsonResponse({"error": "Nenhuma seleção recebida"}, status=400)

    img.selections = selections_json
    img.save()

    # roda o processamento
    polygon = services.apply_deeplab(img)

    return JsonResponse({
        "status": "ok",
        "result_url": None,
        "polygon": polygon
    })

@login_required
@csrf_exempt
def apply_custom_edit(request, image_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método inválido"}, status=405)

    prompt = request.POST.get("prompt")
    mode   = request.POST.get("edit_mode", "local")
    selections_json = request.POST.get("selections_json")  # NOVO PADRÃO

    # 1) prompt obrigatório
    if not prompt or prompt.strip() == "":
        return JsonResponse({"error": "faltando prompt"}, status=400)

    # 2) modo local exige seleção
    if mode == "local":
        if not selections_json or selections_json == "[]":
            return JsonResponse({"error": "selecione uma área primeiro"}, status=400)

        try:
            decoded = json.loads(selections_json)
            selection = decoded[0]
        except Exception:
            return JsonResponse({"error": "seleção inválida"}, status=400)

    # 3) modo full → não tem seleção
    else:
        selection = None  # IMPORTANTÍSSIMO

    # 4) pegar imagem do banco
    processed_image = get_object_or_404(
        ProcessedImage, pk=image_id, user=request.user
    )

    # 5) chamar a IA
    result_url = services.apply_edit_with_prompt(
        request, processed_image, selection, prompt
    )

    return JsonResponse({"status": "ok", "result_url": result_url})





