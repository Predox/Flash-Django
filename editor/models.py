from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
# ---------------- PROFILE -------------------

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    display_name = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Perfil de {self.user.username}"


# ---------------- PRESET -------------------

class Preset(models.Model):
    user = models.ForeignKey(User, related_name="presets", on_delete=models.CASCADE)
    name = models.CharField(max_length=50)

    # parâmetros salvos
    exposure = models.FloatField(default=0)
    contrast = models.FloatField(default=0)
    saturation = models.FloatField(default=0)
    sharpness = models.FloatField(default=0)
    texture = models.FloatField(default=0)
    highlights = models.FloatField(default=0)
    shadows = models.FloatField(default=0)
    whites = models.FloatField(default=0)
    blacks = models.FloatField(default=0)
    background_blur = models.FloatField(default=0)

    def serialize(self):
        """ Para enviar via JSON """
        return {
            "exposure": self.exposure,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "sharpness": self.sharpness,
            "texture": self.texture,
            "highlights": self.highlights,
            "shadows": self.shadows,
            "whites": self.whites,
            "blacks": self.blacks,
            "background_blur": self.background_blur,
        }



# ---------------- PROCESSED IMAGE -------------------

class ProcessedImage(models.Model):
    OPERATION_CHOICES = [
        ('basic_edit', 'Edição básica'),
        ('remove_bg', 'Remoção de fundo'),
        ('inpainting', 'Inpainting / Seleção IA'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='images')
    original_image = models.ImageField(upload_to='originals/')
    result_image = models.ImageField(upload_to='results/', blank=True, null=True)
    operation = models.CharField(max_length=50, choices=OPERATION_CHOICES)
    params = models.JSONField(default=dict, blank=True)
    selections = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.get_operation_display()} - {self.user} - {self.created_at:%d/%m/%Y}'

    def current_image_path(self):
        """
        Retorna o caminho do arquivo que deve ser usado como base:
        - result_image, se existir (imagem já editada)
        - original_image, caso contrário
        """
        if self.result_image and hasattr(self.result_image, "path"):
            return self.result_image.path
        return self.original_image.path


# ---------------- IA LOG -------------------

class IALog(models.Model):
    image = models.ForeignKey(ProcessedImage, on_delete=models.CASCADE, related_name='logs')
    model_name = models.CharField(max_length=100)
    elapsed_ms = models.IntegerField()
    status = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.model_name} - {self.status}'