document.addEventListener("DOMContentLoaded", () => {
  const dropdown = document.getElementById("presetDropdown");
  const trigger = document.getElementById("presetTrigger");
  const menu = document.getElementById("presetMenu");
  const triggerText = document.getElementById("presetTriggerText");

  const slidersForm = document.querySelector(".sliders-form");
  if (!dropdown || !trigger || !menu || !triggerText || !slidersForm) return;

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
  }

  function getImageId() {
    const input = document.querySelector(".sliders-form input[name='image_id']");
    return input ? input.value : null;
  }

  function toggleMenu(forceOpen = null) {
    const isHidden = menu.classList.contains("hidden");
    const shouldOpen = forceOpen === null ? isHidden : forceOpen;
    menu.classList.toggle("hidden", !shouldOpen);
  }

  trigger.addEventListener("click", (e) => {
    e.preventDefault();
    toggleMenu();
  });

  document.addEventListener("click", (e) => {
    if (!dropdown.contains(e.target)) toggleMenu(false);
  });

  function setSlider(name, value) {
    const input = slidersForm.querySelector(`input[name="${name}"]`);
    if (input != null && value != null) input.value = value;
  }

  async function applyCurrentSlidersViaAjax() {
    const imageId = getImageId();
    if (!imageId) return;

    const fd = new FormData();
    fd.append("image_id", imageId);

    slidersForm.querySelectorAll('input[type="range"]').forEach((r) => {
      fd.append(r.name, r.value);
    });

    const res = await fetch("/ajax/apply/", {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      body: fd
    });

    const data = await res.json();

    if (data.image && window.updatePreviewFromBase64) {
      window.updatePreviewFromBase64(data.image);
    }
  }

  async function loadPreset(presetId, presetName) {
    const res = await fetch(`/preset/${presetId}/load/`);
    const data = await res.json();
    if (!data || !data.params) return;

    const p = data.params;

    setSlider("exposure", p.exposure);
    setSlider("contrast", p.contrast);
    setSlider("highlights", p.highlights);
    setSlider("shadows", p.shadows);
    setSlider("whites", p.whites);
    setSlider("blacks", p.blacks);
    setSlider("saturation", p.saturation);
    setSlider("texture", p.texture);
    setSlider("background_blur", p.background_blur);
    setSlider("sharpness", p.sharpness);

    triggerText.textContent = presetName;
    toggleMenu(false);

    await applyCurrentSlidersViaAjax();
  }

  async function deletePreset(presetId, rowEl) {
    const res = await fetch(`/preset/${presetId}/deletar-ajax/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
      }
    });
  
    if (!res.ok) return;
  
    // remove o preset da lista
    rowEl.remove();
  
    // verifica se ainda existem presets
    const remainingPresets = menu.querySelectorAll(".preset-item");
  
    if (remainingPresets.length === 0) {
      // adiciona mensagem de vazio
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "preset-empty";
      emptyDiv.textContent = "Nenhum Preset Criado";
  
      menu.appendChild(emptyDiv);
  
      // reseta o texto do botão
      triggerText.textContent = "Selecione um preset";
    }
  }
  

  menu.addEventListener("click", async (e) => {
    const pickBtn = e.target.closest(".preset-pick");
    const delBtn = e.target.closest(".preset-delete");
    const row = e.target.closest(".preset-item");
    if (!row) return;

    const presetId = row.getAttribute("data-preset-id");

    if (delBtn) {
      e.preventDefault();
      await deletePreset(presetId, row);
      return;
    }

    if (pickBtn) {
      e.preventDefault();
      await loadPreset(presetId, pickBtn.textContent.trim());
    }
  });
});
