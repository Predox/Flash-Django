from django.conf.urls.static import static
from django.conf import settings
from django.urls import path

from . import views

app_name = 'editor'

urlpatterns = [
    path("", views.editor_view, name="editor"),
    path("perfil/", views.profile_view, name="profile"),
    path("update-profile/", views.update_profile, name="update_profile"),
    path("editor/<int:image_id>/", views.editor_open_image, name="editor_with_image"),
    path("imagem/<int:image_id>/remover-fundo/", views.remove_bg_view, name="remove_bg"),
    path("undo-remove-bg/<int:image_id>/", views.undo_remove_bg, name="undo_remove_bg"),
    path("remove-bg-live/", views.remove_bg_live, name="remove_bg_live"),


    path("imagem/<int:image_id>/selecionar-ia/", views.ai_selection_view, name="ai_selection"),

    path("imagem/<int:image_id>/deeplab/", views.deeplab_test_view, name="deeplab_test"),

    path("preset/<int:preset_id>/deletar-ajax/", views.delete_preset_ajax, name="delete_preset_ajax"),

    path("preset/<int:preset_id>/load/", views.load_preset, name="load_preset"),

    path("ajax/apply/", views.ajax_apply_edit, name="ajax_apply_edit"),
    path("apply_deeplab_ajax/<int:image_id>/", views.apply_deeplab_ajax, name="apply_deeplab_ajax"),

    path("apply_custom_edit/<int:image_id>/", views.apply_custom_edit, name="apply_custom_edit")



] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
