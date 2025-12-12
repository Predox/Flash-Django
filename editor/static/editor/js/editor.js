// static/editor/js/editor.js

// ----------------------------------------------------------
// VARIÁVEIS GLOBAIS BÁSICAS
// ----------------------------------------------------------
let canvas, ctx;
let hiddenImg;            
let img = null;           // imagem que será desenhada no canvas

let baseScale = 1;        // escala de "fit" dentro do preview
let scale = 1;            // escala atual (zoom)
let posX = 0;
let posY = 0;

let isDragging = false;
let lastX = 0;
let lastY = 0;




// ----------------------------------------------------------
// FUNÇÃO PARA PEGAR CSRF DO COOKIE (padrão Django)
// ----------------------------------------------------------
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// ----------------------------------------------------------
// FUNÇÃO GLOBAL PARA ATUALIZAR PREVIEW (USADA PELOS PRESETS)
// ----------------------------------------------------------
window.updatePreviewFromBase64 = function (base64Image) {
  const newImg = new Image();
  newImg.onload = () => {
    img = newImg;
    if (hiddenImg) hiddenImg.src = newImg.src;
    fitImageToCanvas();
  };
  newImg.src = "data:image/png;base64," + base64Image;
};


// ----------------------------------------------------------
// DESENHO NO CANVAS
// ----------------------------------------------------------
function drawImageOnCanvas() {
  if (!canvas || !ctx || !img) return;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, posX, posY, img.width * scale, img.height * scale);
}

function fitImageToCanvas() {
  if (!canvas || !ctx || !img) return;

  const container = document.getElementById("canvas");
  const containerWidth = container.clientWidth || 1;
  const containerHeight = container.clientHeight || 1;

  canvas.width = containerWidth;
  canvas.height = containerHeight;

  const imgRatio = img.width / img.height;
  const canvasRatio = containerWidth / containerHeight;

  if (imgRatio > canvasRatio) {
    baseScale = containerWidth / img.width;
  } else {
    baseScale = containerHeight / img.height;
  }

  scale = baseScale;

  posX = (containerWidth - img.width * scale) / 2;
  posY = (containerHeight - img.height * scale) / 2;

  drawImageOnCanvas();
}

// ----------------------------------------------------------
// CARREGAR IMAGEM INICIAL (hidden <img>) 
// ----------------------------------------------------------
function loadInitialImage() {
  if (!hiddenImg || !hiddenImg.src) return;

  img = new Image();
  img.onload = () => {
    fitImageToCanvas();
  };
  img.src = hiddenImg.src;

  // Se a imagem já estiver carregada (cache), força o desenho
  if (hiddenImg.complete) {
    img.onload();
  }
}

// ----------------------------------------------------------
// ZOOM E ARRASTAR
// ----------------------------------------------------------
function setupCanvasInteractions() {
  if (!canvas) return;

  // Zoom com scroll
  canvas.addEventListener(
    "wheel",
    (e) => {
      if (!img) return;
      e.preventDefault();

      const zoomStep = 0.1;
      const direction = e.deltaY < 0 ? 1 : -1;
      let newScale = scale + direction * zoomStep * scale;

      const minScale = baseScale * 0.2;
      const maxScale = baseScale * 5;

      newScale = Math.max(minScale, Math.min(maxScale, newScale));

      // zoom em torno do centro do canvas
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;
      const imgX = (cx - posX) / scale;
      const imgY = (cy - posY) / scale;

      scale = newScale;
      posX = cx - imgX * scale;
      posY = cy - imgY * scale;

      drawImageOnCanvas();
    },
    { passive: false }
  );

  // Arrastar
  canvas.addEventListener("mousedown", (e) => {
    if (!img) return;
    isDragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    canvas.style.cursor = "grabbing";
  });

  window.addEventListener("mouseup", () => {
    isDragging = false;
    canvas.style.cursor = "grab";
  });

  canvas.addEventListener("mousemove", (e) => {
    if (!isDragging || !img) return;

    const dx = e.clientX - lastX;
    const dy = e.clientY - lastY;

    lastX = e.clientX;
    lastY = e.clientY;

    posX += dx;
    posY += dy;

    drawImageOnCanvas();
  });
}

// ----------------------------------------------------------
// AJAX DOS SLIDERS (aplicar ajustes)
// ----------------------------------------------------------
function aplicarAJAX() {
  const imageIdInput = document.querySelector("input[name='image_id']");
  const csrfInput = document.querySelector("[name=csrfmiddlewaretoken]");

  if (!imageIdInput || !csrfInput) return;

  const formData = new FormData();
  formData.append("csrfmiddlewaretoken", csrfInput.value);
  formData.append("image_id", imageIdInput.value);

  document.querySelectorAll(".sliders-form input[type='range']").forEach((slider) => {
    formData.append(slider.name, slider.value);
  });

  fetch("/ajax/apply/", {
    method: "POST",
    body: formData,
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.image) {
        const newImg = new Image();
        newImg.onload = () => {
          img = newImg;
          if (hiddenImg) {
            hiddenImg.src = newImg.src;
          }
          fitImageToCanvas();
        };
        newImg.src = "data:image/png;base64," + data.image;
      }
    })
    .catch((err) => {
      console.error("Erro no AJAX de ajustes:", err);
    });
}

// ----------------------------------------------------------
// SETUP DOS SLIDERS
// ----------------------------------------------------------
function setupSliders() {
  const slidersForm = document.querySelector(".sliders-form");
  if (!slidersForm) return;

  const sliders = slidersForm.querySelectorAll("input[type='range']");
  if (!sliders.length) return;

  let debounceTimer = null;

  sliders.forEach((slider) => {
    slider.addEventListener("input", () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        aplicarAJAX();
      }, 200);
    });
  });
}

document.querySelectorAll('input[type="range"]').forEach(slider => {
  slider.addEventListener("dblclick", () => {
    slider.value = 0;
    aplicarAJAX();
  });
});


// ----------------------------------------------------------
// IMPORTAR (BOTÃO + DRAG & DROP)
// ----------------------------------------------------------
function setupImport() {
  const importBtn = document.getElementById("btn-importar");
  const fileInput = document.getElementById("file-input");
  const dropForm = document.getElementById("drop-form");
  const canvasContainer = document.getElementById("canvas");

  if (importBtn && fileInput && dropForm) {
    importBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => dropForm.submit());
  }

  if (canvasContainer && dropForm && fileInput) {
    canvasContainer.addEventListener("dragover", (e) => {
      e.preventDefault();
      canvasContainer.classList.add("canvas-hover");
    });

    canvasContainer.addEventListener("dragleave", (e) => {
      e.preventDefault();
      canvasContainer.classList.remove("canvas-hover");
    });

    canvasContainer.addEventListener("drop", (e) => {
      e.preventDefault();
      canvasContainer.classList.remove("canvas-hover");

      if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        dropForm.submit();
      }
    });
  }
}

// ----------------------------------------------------------
// MENU HAMBÚRGUER (colapsar sidebar)
// ----------------------------------------------------------
function setupSidebarToggle() {
  const btnHamburger = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");

  if (!btnHamburger || !sidebar) return;

  btnHamburger.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
  });
}

// ----------------------------------------------------------
// INICIALIZAÇÃO
// ----------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  canvas = document.getElementById("editor-canvas");
  ctx = canvas ? canvas.getContext("2d") : null;
  hiddenImg = document.getElementById("original-image");

  setupSidebarToggle();
  setupImport();
  setupSliders();
  setupCanvasInteractions();

  // Carrega a imagem da última edição (se existir)
  loadInitialImage();

  // Reajusta quando a tela mudar de tamanho
  window.addEventListener("resize", () => {
    if (img) {
      fitImageToCanvas();
    }
  });
});



document.getElementById("btn-remove-bg").addEventListener("click", (e) => {
  e.preventDefault();

  canvas.toBlob(async (blob) => {
    if (!blob) {
      alert("Erro ao capturar imagem!");
      return;
    }

    const formData = new FormData();

    const imageIdInput = document.querySelector("input[name='image_id']");
    if (!imageIdInput) {
      alert("Imagem não encontrada no formulário.");
      return;
    }
    const imageId = imageIdInput.value;
    formData.append("image_id", imageId);

    const file = new File([blob], "edited.png", { type: "image/png" });
    formData.append("edited_image", file);

    const response = await fetch("/remove-bg-live/", {
      method: "POST",
      body: formData,
      headers: { "X-CSRFToken": getCookie("csrftoken") }
    });

    const data = await response.json();

    if (data.status === "ok") {
      hiddenImg.src = data.image_url;

      img = new Image();
      img.onload = () => fitImageToCanvas();
      img.src = data.image_url;

    } else {
      alert("Erro ao remover fundo.");
    }

  }, "image/png");
});



// ----------------------------------------------------------
// EXPORTAR CANVAS COMO PNG
// ----------------------------------------------------------
document.getElementById("btn-exportar")?.addEventListener("click", () => {
  const canvas = document.getElementById("editor-canvas");
  if (!canvas) {
    alert("Nenhuma imagem para exportar.");
    return;
  }

  // Converte canvas para PNG
  const dataURL = canvas.toDataURL("image/png");

  // Cria link de download
  const link = document.createElement("a");
  link.href = dataURL;
  link.download = "flash_edit.png"; // nome padrão

  // disparar download
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});

