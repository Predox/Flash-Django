from django import forms
from .models import ProcessedImage, Preset


class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = ProcessedImage
        fields = ['original_image']


class PresetForm(forms.ModelForm):
    class Meta:
        model = Preset
        fields = [
            'name',
            'exposure',
            'contrast',
            'highlights',
            'shadows',
            'whites',
            'blacks',
            'saturation',
            'texture',
            'sharpness',
        ]
