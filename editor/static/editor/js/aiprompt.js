 // Pega o ID da imagem que o Django enviou para o template
 const IMAGE_ID = window.IMAGE_ID;
 const csrftoken = window.CSRF_TOKEN;
 

 // currentSelection deve ser sua seleção refinada pelo DeepLab
 // Ela está sendo atualizada no JS da seleção

function showLoading() {
    const el = document.getElementById("aiLoadingOverlay");
    if (el) el.classList.remove("hidden");
}

function hideLoading() {
    const el = document.getElementById("aiLoadingOverlay");
    if (el) el.classList.add("hidden");
}

async function sendPromptToAI() {
    const imageId = window.IMAGE_ID;
    const prompt = document.getElementById("prompt-input").value;

    const mode = document.querySelector("input[name='edit_mode']:checked").value;
    const selectionsJson = document.getElementById("selectionsInput").value;

    if (!prompt) {
        alert("Digite um prompt!");
        return;
    }

    const formData = new FormData();
    formData.append("prompt", prompt);
    formData.append("edit_mode", mode);
    formData.append("selections_json", selectionsJson);

    try {
        showLoading();

        const res = await fetch(`/apply_custom_edit/${imageId}/`, {
            method: "POST",
            headers: { "X-CSRFToken": getCSRFToken() },
            body: formData
        });

        const data = await res.json();
        console.log("RESULTADO IA:", data);

        if (data.status !== "ok") {
            hideLoading();
            alert("Erro IA: " + data.error);
            return;
        }

        const newUrl = data.result_url;

        const imgEl = document.getElementById("selection-hidden-img");

        imgEl.onload = () => {
            console.log("Nova imagem carregada!");
            hideLoading();
            drawImage(); // redesenha o canvas
        };

        // força recarregamento evitando cache
        const finalSrc = newUrl + "?t=" + Date.now();
        imgEl.src = finalSrc;

        // atualiza imagem dentro do canvas
        if (window.updateMainImage) {
            window.updateMainImage(finalSrc);
        }
        window.location.reload(true);

    } catch (err) {
        hideLoading();
        console.error("Erro IA:", err);
        alert("Falha ao comunicar com IA.");
    }
}
