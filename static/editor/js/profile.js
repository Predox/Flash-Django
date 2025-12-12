// Abrir / Fechar modal
const modal = document.getElementById("profile-modal");
const openBtn = document.getElementById("open-profile-modal");
const closeBtn = document.getElementById("close-profile-modal");
const cancelBtn = document.getElementById("cancel-profile-edit");

openBtn.addEventListener("click", () => modal.classList.remove("hidden"));
closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
cancelBtn.addEventListener("click", () => modal.classList.add("hidden"));

// Preview da foto
const photoInput = document.getElementById("photo-input");
const preview = document.getElementById("photo-preview");

photoInput.addEventListener("change", () => {
    const file = photoInput.files[0];
    if (file) {
        preview.src = URL.createObjectURL(file);
    }
});
