document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("selectionCanvas");
    const tooltip = document.getElementById("selectionTooltip");
    const removeLastBtn = document.getElementById("btnRemoveLast");
    const clearBtn = document.getElementById("btnClearSelections");
    const selectionsInput = document.getElementById("selectionsInput");

    const hiddenImg = document.getElementById("selection-hidden-img");

    // IMAGEM PRINCIPAL
    const img = new Image();
    img.src = hiddenImg.src;

    // ESTADO
    let selections = [];
    let currentPath = [];
    let isDrawing = false;
    let dashOffset = 0;

    // OBJETOS INDEPENDENTES (as seleções azuis)
    let floatingObjects = [];
    let clickStartTime = 0;
    let clickedOnObject = null;

    // POPUP
    const popup = document.getElementById("selectionPopup");
    const popupCloseBtn = document.getElementById("popupClose");
    const popupDeleteBtn = document.getElementById("popupDelete");
    let selectedObject = null;

    window.updateMainImage = function(newSrc) {
        img.src = newSrc;
        img.onload = () => drawImage();
    };

    function openPopup(x, y, obj) {
        if (!popup) return;
        selectedObject = obj;
        popup.style.left = `${x + 10}px`;
        popup.style.top = `${y + 10}px`;
        popup.classList.remove("hidden");
    }

    function closePopup() {
        if (!popup) return;
        popup.classList.add("hidden");
        selectedObject = null;
    }

    if (popupDeleteBtn) {
        popupDeleteBtn.onclick = () => {
            if (selectedObject) {
        
                // 1) remove o objeto azul
                floatingObjects = floatingObjects.filter(o => o !== selectedObject);
        
                // 2) remove também a seleção tracejada
                selections = [];
        
                // 3) atualiza o campo hidden
                updateHiddenField();
        
                // 4) fecha o popup e redesenha
                closePopup();
                drawImage();
            }
        };
        
    }

    if (popupCloseBtn) {
        popupCloseBtn.onclick = closePopup;
    }

    // ------------------------------------------------------------
    // VER SE ESTÁ DENTRO DA IMAGEM
    // ------------------------------------------------------------
    function isInsideImage(px, py) {
        if (!img.drawPos) return false;

        const { x, y, w, h } = img.drawPos;
        return px >= x && px <= x + w && py >= y && py <= y + h;
    }

    function clampPolygonToImage(path, drawPos) {
        const { x, y, w, h } = drawPos;
    
        return path.map(p => ({
            x: Math.min(Math.max(p.x, x), x + w),
            y: Math.min(Math.max(p.y, y), y + h)
        }));
    }
    

    // ------------------------------------------------------------
    // RESIZE DO CANVAS
    // ------------------------------------------------------------
    function resizeCanvas() {
        const preview = document.getElementById("ai-preview");

        canvas.width = preview.clientWidth;
        canvas.height = preview.clientHeight;

        drawImage();
    }

    // ------------------------------------------------------------
    // DESENHA A IMAGEM, OBJETOS E SELEÇÕES
    // ------------------------------------------------------------
    function drawImage() {
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!img.width || !img.height) return;

        // 1) calcular como encaixar a imagem no canvas
        const scale = Math.min(
            canvas.width / img.width,
            canvas.height / img.height
        );

        const w = img.width * scale;
        const h = img.height * scale;
        const x = (canvas.width - w) / 2;
        const y = (canvas.height - h) / 2;

        img.drawPos = { x, y, w, h, scale };

        // 2) desenhar imagem base
        ctx.drawImage(img, x, y, w, h);

        // 3) desenhar seleções independentes (azuis)
        floatingObjects.forEach(obj => {
            ctx.save();
            ctx.translate(obj.x, obj.y);

            ctx.beginPath();
            ctx.moveTo(obj.path[0].x, obj.path[0].y);
            obj.path.forEach(pt => ctx.lineTo(pt.x, pt.y));
            ctx.closePath();

            // preenchimento azul translúcido
            ctx.fillStyle = "rgba(15, 30, 60, 0.45)";
            ctx.fill();

            // borda azul
            ctx.strokeStyle = "rgba(60, 120, 255, 0.8)";
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.restore();
        });

        // 4) desenhar o traço branco enquanto desenha
        selections.forEach(s => drawPath(ctx, s.path));
        if (currentPath.length > 1) drawPath(ctx, currentPath);
    }

    // ------------------------------------------------------------
    // DESENHAR LINHAS DE SELEÇÃO (pontilhado)
    // ------------------------------------------------------------
    function drawPath(ctx, path) {
        ctx.beginPath();
        ctx.moveTo(path[0].x, path[0].y);
    
        path.forEach(pt => ctx.lineTo(pt.x, pt.y));
    
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
    
        ctx.setLineDash([6, 4]);
        ctx.lineDashOffset = -dashOffset;
    
        ctx.stroke();
        ctx.setLineDash([]);
    }
    
    function animateSelection() {
        dashOffset += 0.5; // velocidade do movimento (0.3 a 1)
        drawImage();
        requestAnimationFrame(animateSelection);
    }
    
    requestAnimationFrame(animateSelection);
    

    // ------------------------------------------------------------
    // CONVERTE COORDENADAS DO MOUSE PARA O CANVAS
    // ------------------------------------------------------------
    function getCoords(e) {
        const rect = canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    function interpolatePath(path, step = 2) {
        const newPath = [];

        for (let i = 0; i < path.length - 1; i++) {
            const p1 = path[i];
            const p2 = path[i + 1];

            const dx = p2.x - p1.x;
            const dy = p2.y - p1.y;

            const dist = Math.sqrt(dx * dx + dy * dy);
            const segments = Math.max(1, Math.round(dist / step));

            for (let j = 0; j < segments; j++) {
                const t = j / segments;
                newPath.push({
                    x: p1.x + dx * t,
                    y: p1.y + dy * t
                });
            }
        }

        // Último ponto
        newPath.push(path[path.length - 1]);

        return newPath;
    }


    // ------------------------------------------------------------
    // CALCULA BOUNDING BOX DO POLÍGONO
    // ------------------------------------------------------------
    function getPolygonBounds(path) {
        const xs = path.map(p => p.x);
        const ys = path.map(p => p.y);

        return {
            x: Math.min(...xs),
            y: Math.min(...ys),
            w: Math.max(...xs) - Math.min(...xs),
            h: Math.max(...ys) - Math.min(...ys)
        };
    }

    // ------------------------------------------------------------
    // CRIA OBJETO INDEPENDENTE A PARTIR DA SELEÇÃO
    // ------------------------------------------------------------
    function createFloatingObjectFromSelection(path) {
        // calcula bounding box 
        const { x, y, w, h } = getPolygonBounds(path);
    
        // salva path em coordenadas relativas ao bounding box
        const relative = path.map(p => ({
            x: p.x - x,
            y: p.y - y
        }));
    
        floatingObjects.push({
            path: relative,
            x, y, w, h
        });
    
        drawImage();
    }
    
    

    function smoothSpline(path, tension = 0.5, segments = 16) {
        if (path.length < 3) return path;

        const result = [];

        for (let i = 0; i < path.length - 1; i++) {
            const p0 = path[i - 1] || path[i];
            const p1 = path[i];
            const p2 = path[i + 1] || p1;
            const p3 = path[i + 2] || p2;

            for (let t = 0; t <= 1; t += 1 / segments) {
                const tt = t * t;
                const ttt = tt * t;

                const q1 = -tension * t + 2 * tension * tt - tension * ttt;
                const q2 = 1 + (tension - 3) * tt + (2 - tension) * ttt;
                const q3 = tension * t + (3 - 2 * tension) * tt + (tension - 2) * ttt;
                const q4 = -tension * tt + tension * ttt;

                const x = p0.x * q1 + p1.x * q2 + p2.x * q3 + p3.x * q4;
                const y = p0.y * q1 + p1.y * q2 + p2.y * q3 + p3.y * q4;

                result.push({ x, y });
            }
        }

        return result;
    }


    // ------------------------------------------------------------
    // PONTO DENTRO DE POLÍGONO (para clique na seleção)
    // ------------------------------------------------------------
    function pointInPolygon(px, py, polygon) {
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i].x, yi = polygon[i].y;
            const xj = polygon[j].x, yj = polygon[j].y;

            const intersect =
                (yi > py) !== (yj > py) &&
                px < ((xj - xi) * (py - yi)) / (yj - yi) + xi;

            if (intersect) inside = !inside;
        }
        return inside;
    }

    // ------------------------------------------------------------
    // EVENTOS DO CANVAS
    // ------------------------------------------------------------
    canvas.onmousedown = (e) => {
        const pos = getCoords(e);
        clickStartTime = performance.now();
    
        closePopup(); // fecha popup
    
        // 1) SE CLICAR EM CIMA DE UM OBJETO → ABRE POPUP E NÃO DESENHA
        for (let obj of floatingObjects) {
            const absolutePath = obj.path.map(p => ({
                x: p.x + obj.x,
                y: p.y + obj.y
            }));
    
            if (pointInPolygon(pos.x, pos.y, absolutePath)) {
                // apenas guarda que clicou, popup vem no mouseup
                clickedOnObject = obj;
                return; // IMPEDIR DESENHO
            }
        }
    
        // 2) Se não clicou em objeto → começa desenho normal
        if (!isInsideImage(pos.x, pos.y)) return;
    
        clickedOnObject = null;
        isDrawing = true;
        currentPath = [pos];
    };
    

    canvas.onmousemove = (e) => {
        const pos = getCoords(e);
    
        
    
        // desenhando seleção (AGORA PODE DESENHAR FORA DA IMAGEM)
        if (isDrawing) {
            currentPath.push(pos);
            drawImage();
        }
    };
    

    canvas.onmouseup = (e) => {
        const pos = getCoords(e);
        const clickDuration = performance.now() - clickStartTime;

        

        


        if (isDrawing && currentPath.length > 2) {

            // FECHA o polígono ANTES da suavização
            const closed = [...currentPath, currentPath[0]];
        
            // spline SUAVE (curvas melhores)
            let smoothPath = smoothSpline(closed, 0.5, 20);
        
            // remover duplicata final
            if (
                smoothPath.length > 2 &&
                smoothPath[0].x === smoothPath[smoothPath.length - 1].x &&
                smoothPath[0].y === smoothPath[smoothPath.length - 1].y
            ) {
                smoothPath.pop();
            }
        
            // interpolar para mais pontos (contorno mais denso)
            smoothPath = interpolatePath(smoothPath, 1.5);
        
            const selection = { path: smoothPath };
        
            // salva apenas uma vez
            selections = [selection];
        
            updateHiddenField();
        
            // remove objetos antigos
            floatingObjects = [];
        
            createFloatingObjectFromSelection(smoothPath);
        
            isDrawing = false;
            currentPath = [];
            drawImage();
        
// permite desenhar fora da imagem normalmente
currentPath.push(pos);
drawImage();



            sendSelectionToBackend(selection);
            return;
        }
        

        // 3) Clique rápido em cima de uma seleção (sem arrastar)
        if (clickDuration < 200) {
            for (let obj of floatingObjects) {
                const absolutePath = obj.path.map(p => ({
                    x: p.x + obj.x,
                    y: p.y + obj.y
                }));

                if (pointInPolygon(pos.x, pos.y, absolutePath)) {
                    openPopup(pos.x, pos.y, obj);
                    return;
                }
            }
        }

        isDrawing = false;
        currentPath = [];
        drawImage();
    };

    // ------------------------------------------------------------
    // BOTÕES DO TOOLTIP ORIGINAL
    // ------------------------------------------------------------
    removeLastBtn.onclick = () => {
        selections.pop();
        updateHiddenField();
        drawImage();
    };

    clearBtn.onclick = () => {
        selections = [];
        floatingObjects = [];
        updateHiddenField();
        drawImage();
    };

    function updateHiddenField() {
        selectionsInput.value = JSON.stringify(selections);
    }

    // ------------------------------------------------------------
    // CARREGAR IMAGEM E AJUSTAR CANVAS
    // ------------------------------------------------------------
    img.onload = resizeCanvas;
    window.addEventListener("resize", resizeCanvas);

    // ------------------------------------------------------------
    // ENVIAR SELEÇÃO AO BACKEND AUTOMATICAMENTE
    // ------------------------------------------------------------

    function convertSelectionToImageSpace(selection) {
        if (!img.drawPos) return selection;

        const { x: offX, y: offY, scale } = img.drawPos;

        const convertedPath = selection.path.map(p => ({
            x: (p.x - offX) / scale,
            y: (p.y - offY) / scale
        }));

        return { path: convertedPath };
    }


    async function sendSelectionToBackend(selection) {
        const imageId = parseInt(window.IMAGE_ID);

        const converted = convertSelectionToImageSpace(selection);

        const formData = new FormData();
        formData.append("selections", JSON.stringify([converted]));

        try {
            const res = await fetch(`/apply_deeplab_ajax/${imageId}/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCSRFToken()
                },
                body: formData
            });

            const data = await res.json();

            if (data.status === "ok") {

                // Pegamos os valores corretos da imagem no canvas
                const scale = img.drawPos.scale;
                const offsetX = img.drawPos.x;
                const offsetY = img.drawPos.y;
            
                // 1) Converter o polígono da imagem → canvas
                let refinedPath = data.polygon.map(p => ({
                    x: p.x * scale + offsetX,
                    y: p.y * scale + offsetY
                }));
            
                // 2) FECHAR para spline
                refinedPath.push(refinedPath[0]);
            
                // 3) suavizar com spline
                refinedPath = smoothSpline(refinedPath, 0.5, 32);
            
                // 4) interpolar para mais densidade
                refinedPath = interpolatePath(refinedPath, 1.5);
                window.currentSelection = { path: refinedPath };
            
                // 5) remover duplicata final
                refinedPath.pop();
            
                // 6) impedir polígono de sair da imagem
                refinedPath = clampPolygonToImage(refinedPath, img.drawPos);
            
                // 7) atualizar seleção exibida
                floatingObjects = [];
                selections = [{ path: refinedPath }];
            
                createFloatingObjectFromSelection(refinedPath);
                drawImage();
            }
            


        } catch (err) {
            console.error("Erro no fetch DeepLab:", err);
        }

        console.log("SELECTION ENVIADA:", JSON.stringify([converted]));
    }




});


