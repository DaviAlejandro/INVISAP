document.addEventListener("DOMContentLoaded", function () {
    const formulario = document.getElementById("formEditarProyecto");
      
    if (!formulario) return;

    const fechaPlan = document.getElementById("fecha_p") || document.getElementsByName("fecha_p")[0];
    const observaciones = document.getElementById("observaciones") || document.getElementsByName("observaciones")[0];
    const moneda = document.getElementById("moneda_p");
    const estimacion = document.getElementById("estimacion_p") || document.getElementsByName("estimacion_p")[0];

    function obtenerMontoEstimacion() {
        if (!estimacion) return "";
        return estimacion.value.trim().replace(/^(BS|USD)\s*/i, "");
    }

    function formatearEstimacion() {
        if (!estimacion) return;

        let valor = obtenerMontoEstimacion().replace(/\D/g, "");
        if (valor === "") {
            estimacion.value = "";
            return;
        }

        let entero = parseInt(valor, 10);
        if (isNaN(entero)) {
            estimacion.value = "";
            return;
        }

        let opciones = { minimumFractionDigits: 2, maximumFractionDigits: 2 };
        estimacion.value = (entero / 100).toLocaleString("de-DE", opciones);
        marcarValido(estimacion);
    }

    function marcarInvalido(input, mensaje) {
        if (!input) return;
        input.classList.remove("is-valid");
        input.classList.add("is-invalid");
        
        let contenedorPadre = input.parentElement;
        if (contenedorPadre.classList.contains("input-group")) {
            contenedorPadre = contenedorPadre.parentElement;
        }

        let feedback = contenedorPadre.querySelector(".invalid-feedback");
        if (!feedback) {
            feedback = document.createElement("div");
            feedback.className = "invalid-feedback d-block";
            contenedorPadre.appendChild(feedback);
        }
        feedback.innerText = mensaje;
    }

    function marcarValido(input) {
        if (!input) return;
        input.classList.remove("is-invalid");
        input.classList.add("is-valid");
        
        let contenedorPadre = input.parentElement;
        if (contenedorPadre.classList.contains("input-group")) {
            contenedorPadre = contenedorPadre.parentElement;
        }
        
        const feedback = contenedorPadre.querySelector(".invalid-feedback");
        if (feedback) {
            feedback.remove();
        }
    }

  
    if (estimacion) {
        if (moneda) {
            const monedaActual = estimacion.value.match(/^\s*(BS|USD)\b/i);
            moneda.value = monedaActual ? monedaActual[1].toUpperCase() : 'BS';
            estimacion.value = obtenerMontoEstimacion();
        }

        estimacion.addEventListener("input", formatearEstimacion);

        estimacion.addEventListener("focus", function() {
            if(estimacion.value === "0,00") {
                estimacion.value = "";
            }
        });
    }

    if (observaciones) {
        observaciones.addEventListener("input", function () {
            if (observaciones.value.trim().length >= 10) {
                marcarValido(observaciones);
            } else {
                marcarInvalido(observaciones, "La descripción técnica debe tener al menos 10 caracteres.");
            }
        });
    }

    formulario.addEventListener("submit", function (e) {
        let tieneErrores = false;

        
        if (fechaPlan) {
            if (!fechaPlan.value) {
                marcarInvalido(fechaPlan, "Por favor, seleccione una fecha de planificación.");
                tieneErrores = true;
            } else {
                marcarValido(fechaPlan);
            }
        }

        
        if (observaciones) {
            if (observaciones.value.trim().length < 10) {
                marcarInvalido(observaciones, "La descripción técnica debe tener al menos 10 caracteres.");
                tieneErrores = true;
            } else {
                marcarValido(observaciones);
            }
        }

        // Validar maquinaria: al menos una seleccionada
        const maquinariaContainer = document.getElementById('maquinaria_container');
        const maquinariaSelects = maquinariaContainer ? maquinariaContainer.querySelectorAll('.maquinaria_select') : [];
        let maquinariaValida = false;
        maquinariaSelects.forEach(select => {
            if (select.value && select.value.trim() !== '') {
                maquinariaValida = true;
            }
        });
        
        if (!maquinariaValida) {
            if (maquinariaSelects.length > 0) {
                marcarInvalido(maquinariaSelects[0], 'Debe seleccionar al menos una maquinaria.');
            }
            tieneErrores = true;
        } else {
            if (maquinariaSelects.length > 0) {
                marcarValido(maquinariaSelects[0]);
            }
        }

        const computosContainer = document.getElementById('computos_metricos_container');
        const computosItems = computosContainer ? computosContainer.querySelectorAll('.computos_metrico_item') : [];
        let computosValidos = [];

        computosItems.forEach(item => {
            const metrica = item.querySelector('.computos_metrica');
            const opcion = item.querySelector('.computos_opcion');
            const costo = item.querySelector('.computos_costo');
            if (metrica && metrica.value && opcion && opcion.value.trim() && costo && costo.value.trim()) {
                computosValidos.push({
                    metrica: metrica.value,
                    opcion: opcion.value.trim(),
                    costo: costo.value.trim()
                });
            }
        });

        if (computosValidos.length === 0) {
            tieneErrores = true;
            if (computosContainer) {
                computosContainer.classList.add('is-invalid');
                let fb = computosContainer.parentElement.querySelector('.invalid-feedback');
                if (!fb) {
                    fb = document.createElement('div');
                    fb.className = 'invalid-feedback d-block';
                    computosContainer.parentElement.appendChild(fb);
                }
                fb.textContent = 'Debe agregar al menos un cómputo métrico.';
            }
        } else {
            if (computosContainer) {
                computosContainer.classList.remove('is-invalid');
                const fb = computosContainer.parentElement.querySelector('.invalid-feedback');
                if (fb) fb.remove();
            }
        }

        if (tieneErrores) {
            e.preventDefault(); 
            const primerError = formulario.querySelector(".is-invalid");
            if (primerError) primerError.focus();
        } else {
            const hiddenComputos = document.getElementById('computos_p');
            if (hiddenComputos) {
                hiddenComputos.value = JSON.stringify(computosValidos);
            }
            if (moneda && estimacion) {
                const monto = obtenerMontoEstimacion();
                if (monto.trim()) {
                    estimacion.value = `${moneda.value} ${monto}`;
                }
            }
        }
    });
});