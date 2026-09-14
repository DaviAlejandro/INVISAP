// --- FUNCIÓN DE REGISTRO ---
function formatFecha(fecha) {
    if (!fecha) return '—';
    if (typeof fecha === 'string' && fecha.includes('-')) {
        return fecha;
    }
    const d = new Date(fecha);
    if (isNaN(d.getTime())) return fecha;
    const año = d.getFullYear();
    const mes = String(d.getMonth() + 1).padStart(2, '0');
    const dia = String(d.getDate()).padStart(2, '0');
    const hora = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    const seg = String(d.getSeconds()).padStart(2, '0');
    return `${año}-${mes}-${dia} ${hora}:${min}:${seg}`;
}

function marcarInvalidoCustom(input, mensaje) {
    if (!input) return;
    input.classList.add('is-invalid');
    let cont = input.parentElement;
    while (cont && !cont.classList.contains('col-md-6') && !cont.classList.contains('col-md-4') && !cont.classList.contains('form-group')) {
        cont = cont.parentElement;
    }
    if (cont && cont.classList.contains('input-group')) cont = cont.parentElement;
    let fb = cont && cont.querySelector('.invalid-feedback');
    if (!fb && cont) { fb = document.createElement('div'); fb.className = 'invalid-feedback d-block'; cont.appendChild(fb); }
    if (fb) fb.textContent = mensaje;
}

document.getElementById('btnGuardarProyecto').addEventListener('click', function() {
    const form = document.getElementById('formRegistrarProyecto');
    if (!form) return;

    const solicitudId = document.getElementById('solicitud_id_p');
    const errorSolicitudDiv = document.getElementById('solicitud_error_message');
    const fechaPlan = document.getElementById('fecha_p');
    const observaciones = document.getElementById('observaciones');
    const codigoProyecto = document.getElementById('Codigo_p');
    const estimacion = document.getElementById('estimacion_p');

    let tieneErrores = false;

    if (!solicitudId.value) {
        if (errorSolicitudDiv) {
            errorSolicitudDiv.classList.remove('d-none');
            errorSolicitudDiv.textContent = 'Debe seleccionar una solicitud.';
        }
        tieneErrores = true;
    } else {
        if (errorSolicitudDiv) errorSolicitudDiv.classList.add('d-none');
    }

    if (!fechaPlan || !fechaPlan.value) {
        marcarInvalidoCustom(fechaPlan, 'Debe seleccionar una fecha de planificación.');
        tieneErrores = true;
    } else {
        fechaPlan.classList.remove('is-invalid');
        fechaPlan.classList.add('is-valid');
    }

    if (!observaciones || observaciones.value.trim().length < 10) {
        marcarInvalidoCustom(observaciones, 'La descripción técnica debe tener al menos 10 caracteres.');
        tieneErrores = true;
    } else {
        observaciones.classList.remove('is-invalid');
        observaciones.classList.add('is-valid');
    }

    if (!codigoProyecto || codigoProyecto.value.trim() === '' || codigoProyecto.value.trim().length < 5) {
        marcarInvalidoCustom(codigoProyecto, 'El código del proyecto es obligatorio (Ej: PRY-001).');
        tieneErrores = true;
    } else {
        codigoProyecto.classList.remove('is-invalid');
        codigoProyecto.classList.add('is-valid');
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
        // Marcar el primer select como inválido
        if (maquinariaSelects.length > 0) {
            marcarInvalidoCustom(maquinariaSelects[0], 'Debe seleccionar al menos una maquinaria.');
        }
        tieneErrores = true;
    } else {
        if (maquinariaSelects.length > 0) {
            maquinariaSelects[0].classList.remove('is-invalid');
            maquinariaSelects[0].classList.add('is-valid');
        }
    }

    const computosContainer = document.getElementById('computos_metricos_container');
    const computosItems = computosContainer ? computosContainer.querySelectorAll('.computos_metrico_item') : [];
    let computosValidos = [];
    let computosTieneError = false;

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
        computosTieneError = true;
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
        tieneErrores = true;
    } else {
        if (computosContainer) {
            computosContainer.classList.remove('is-invalid');
            const fb = computosContainer.parentElement.querySelector('.invalid-feedback');
            if (fb) fb.remove();
        }
    }

    if (!estimacion || estimacion.value.trim() === '') {
        marcarInvalidoCustom(estimacion, 'La estimación de costo es obligatoria.');
        tieneErrores = true;
    } else {
        estimacion.classList.remove('is-invalid');
        estimacion.classList.add('is-valid');
    }

    if (tieneErrores) {
        const primerError = form.querySelector('.is-invalid');
        if (primerError) primerError.focus();
        return;
    }

    if (codigoProyecto && codigoProyecto.value.trim() !== '') {
        const validarCodigo = codigoProyecto.value.trim();
        fetch(`/api/proyecto/validar-codigo/${validarCodigo}`, { method: 'GET' })
        .then(r => r.json())
        .then(val => {
            if (val.existe_eliminado) {
                marcarInvalidoCustom(codigoProyecto, 'Este código se usó en un proyecto eliminado anteriormente. Elija otro código.');
                codigoProyecto.focus();
                return;
            }
            if (val.existe_activo) {
                marcarInvalidoCustom(codigoProyecto, 'El código ya existe en un proyecto activo. Elija otro código.');
                codigoProyecto.focus();
                return;
            }
            const hiddenComputos = document.getElementById('computos_p');
            if (hiddenComputos) {
                hiddenComputos.value = JSON.stringify(computosValidos);
            }
            enviarFormulario(form);
        });
    } else {
        const hiddenComputos = document.getElementById('computos_p');
        if (hiddenComputos) {
            hiddenComputos.value = JSON.stringify(computosValidos);
        }
        enviarFormulario(form);
    }
});

function enviarFormulario(form) {
    const moneda = document.getElementById('moneda_p');
    const estimacion = document.getElementById('estimacion_p');
    if (moneda && estimacion && estimacion.value.trim()) {
        estimacion.value = moneda.value + ' ' + estimacion.value;
    }
    const formData = new FormData(form);
    fetch(form.action, { method: 'POST', body: formData })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('modalRegistrarProyecto')).hide();

            Swal.fire('¡Éxito!', data.message, 'success').then(() => {
                const p = data.data;
                const tableBody = document.querySelector('table tbody');
                const msgVacio = document.getElementById('mensaje-vacio');
                if (msgVacio) msgVacio.remove();

                const newRow = `
                    <tr>
                        <td>${tableBody.rows.length + 1}</td>
                        <td class="fw-bold text-secondary">${p.codigo_proyecto}</td>
                        <td>${formatFecha(p.fecha_planificacion)}</td>
                        <td class="text-uppercase">${p.nombre_solicitante || '—'}</td>
                        <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${p.descripcion_tecnica || '—'}</td>
                        <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${p.computos_metricos_texto || '—'}</td>
                        <td>${p.problematica || '—'}</td>
                        <td><span class="badge bg-dark">${p.nombre_maquinaria || 'PENDIENTE'}</span></td>
                        <td><span class="badge bg-info">${p.nombre_proyectista || 'Sin asignar'}</span></td>
                        <td class="text-success fw-bold">${p.estimacion_costo}</td>
                        <td class="text-center">
                            <div class="d-flex gap-1 justify-content-center">
                                <button type="button" class="btn btn-sm btn-outline-info" title="Ver detalle"
                                    data-bs-toggle="modal" data-bs-target="#modalDetalleProyecto"
                                    data-codigo="${p.codigo_proyecto}"
                                    data-fecha="${p.fecha_planificacion}"
                                    data-solicitante="${p.nombre_solicitante || '—'}"
                                    data-tipo="${p.tipo_solicitud || '—'}"
                                    data-descripcion="${p.descripcion_tecnica || '—'}"
                                    data-problematica="${p.problematica || '—'}"
                                    data-computos="${p.computos_metricos_texto || '—'}"
                                    data-costo="${p.estimacion_costo || '0.00'}"
                                    data-maquinaria="${p.nombre_maquinaria || 'PENDIENTE'}"
                                    data-proyectista="${p.nombre_proyectista || 'Sin asignar'}">
                                    <i class="bx bx-show"></i>
                                </button>
                                <a href="/editar-proyecto/${p.codigo_proyecto}" class="btn btn-sm btn-outline-warning"><i class="bx bx-edit"></i></a>
                                <button type="button" class="btn btn-sm btn-outline-danger" onclick="confirmarEliminacion(this)" data-delete-url="/eliminar-proyecto/${p.codigo_proyecto}"><i class="bx bx-trash"></i></button>
                            </div>
                        </td>
                    </tr>`;
                
                tableBody.insertAdjacentHTML('beforeend', newRow);
                form.reset();
                const allInvalids = form.querySelectorAll('.is-invalid');
                allInvalids.forEach(el => el.classList.remove('is-invalid'));
                
                const computosContainer = document.getElementById('computos_metricos_container');
                if (computosContainer) {
                    computosContainer.innerHTML = `
                        <div class="computos_metrico_item input-group shadow-sm mb-2" data-index="0">
                          <select class="form-select computos_metrica" name="computos_metrica_0" style="max-width: 120px;" required>
                            <option value="" selected disabled>Métrica</option>
                            <option value="m2">m2</option>
                            <option value="m3">m3</option>
                            <option value="ml">ml</option>
                            <option value="unidades">unidades</option>
                            <option value="kg">kg</option>
                            <option value="lt">lt</option>
                          </select>
                          <input type="text" class="form-control computos_opcion" name="computos_opcion_0" placeholder="Ej: asfalto" list="opciones_computos_list" required />
                          <input type="number" class="form-control computos_costo" name="computos_costo_0" placeholder="Cantidad" style="max-width: 140px;" min="0" step="0.01" required />
                          <button type="button" class="btn btn-outline-danger btn-eliminar-computo" style="display: none;">
                            <i class="bx bx-trash"></i>
                          </button>
                        </div>
                    `;
                    initComputosMetricos('computos_metricos_container');
                }
                
                const maquinariaContainer = document.getElementById('maquinaria_container');
                if (maquinariaContainer) {
                    const firstSelect = maquinariaContainer.querySelector('.maquinaria_select');
                    let optionsHTML = '<option value="" selected disabled>Seleccione maquinaria...</option>';
                    if (firstSelect) {
                        Array.from(firstSelect.options).forEach(opt => {
                            if (opt.value) {
                                optionsHTML += `<option value="${opt.value}">${opt.text}</option>`;
                            }
                        });
                    }
                    maquinariaContainer.innerHTML = `
                        <div class="maquinaria_item input-group shadow-sm mb-2" data-index="0">
                          <select class="form-select maquinaria_select" name="maquinaria_0" required>
                            ${optionsHTML}
                          </select>
                          <button type="button" class="btn btn-outline-danger btn-eliminar-maquinaria" style="display: none;">
                            <i class="bx bx-trash"></i>
                          </button>
                        </div>
                    `;
                    if (typeof window.initMaquinaria === 'function') {
                        window.initMaquinaria('maquinaria_container');
                    }
                }
                
                const formRegistrarProyecto = document.getElementById('formRegistrarProyecto');
                if (formRegistrarProyecto) {
                    if (typeof ValidacionesComunes !== 'undefined') {
                        ValidacionesComunes.initSelects(formRegistrarProyecto);
                        ValidacionesComunes.initBotonesSubmit(formRegistrarProyecto, { textoGuardando: 'Registrando...' });
                    }
                }
                
                actualizarContador(1);
            });
        } else {
            Swal.fire('Error', data.message, 'error');
        }
    });
}

function confirmarEliminacion(btn) {
    const url = btn.getAttribute('data-delete-url');
    const row = btn.closest('tr');
    const tableBody = row.parentNode;

    Swal.fire({
        title: '¿Estás seguro?',
        text: "¡No podrás revertir esta acción!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        confirmButtonText: 'Sí, eliminar'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(url, { method: 'GET' })
            .then(response => {
                if (response.ok) {
                    row.remove();
                    actualizarContador(-1);
                    if (tableBody.querySelectorAll('tr').length === 0) {
                        tableBody.insertAdjacentHTML('beforeend', 
                            '<tr id="mensaje-vacio"><td colspan="11" class="text-center text-muted py-4">NO SE ENCUENTRAN PROYECTOS GESTIONADOS</td></tr>');
                    }
                    Swal.fire('Eliminado', 'Proyecto eliminado.', 'success');
                }
            });
        }
    });
}

function actualizarContador(cambio) {
    const contadorEl = document.getElementById('contador-total');
    if (contadorEl) {
        let actual = parseInt(contadorEl.innerText) || 0;
        contadorEl.innerText = actual + cambio;
    }
}