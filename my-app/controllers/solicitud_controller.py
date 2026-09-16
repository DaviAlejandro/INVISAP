from flask import session, request, jsonify
from models.model_solicitudes import SolicitudModel
from models.model_prioridad import PrioridadModel
from services.ia_prioridad_service import priorizar_solicitud_async, iniciar_scheduler, detener_scheduler
from services.bitacora_service import BitacoraService


def crear_solicitud_async(datos_formulario, session_data=None):
    try:
        modelo = SolicitudModel()
        modelo.set_tipo_solicitud(datos_formulario.get('tipo_solicitud'))
        modelo.set_estatus_solicitud(datos_formulario.get('estatus'))
        modelo.set_problematica(datos_formulario.get('problematica'), datos_formulario.get('tipo_problematica'))
        modelo.set_fecha()
        modelo.set_solicitante_data(datos_formulario)

        nuevo_id = modelo.guardar()
        if nuevo_id:
            responsable = session_data.get('name_surname', 'Sistema') if session_data else 'Sistema'
            BitacoraService.registrar_accion(
                session=session_data,
                modulo='Solicitudes',
                accion='CREAR',
                descripcion=f'Solicitud #{nuevo_id} creada y priorización asíncrona iniciada'
            )
            priorizar_solicitud_async(nuevo_id, datos_formulario.get('tipo_solicitud'))
            return {'success': True, 'id': nuevo_id, 'message': 'Solicitud registrada. Priorización en proceso.'}
        return {'success': False, 'message': 'Error en la base de datos al guardar.'}
    except ValueError as e:
        return {'success': False, 'message': str(e)}
    except Exception as e:
        print(f"[solicitud_controller] Error: {e}")
        return {'success': False, 'message': 'Error interno del servidor.'}


def obtener_solicitud_por_id(id_solicitud):
    if not id_solicitud:
        return None
    return SolicitudModel.buscar_por_id(id_solicitud)


def actualizar_y_reclasificar(id_solicitud, datos_formulario, session_data=None):
    try:
        modelo = SolicitudModel(id_solicitudes=id_solicitud)
        modelo.set_estatus_solicitud(datos_formulario.get('estatus', datos_formulario.get('estatus_solicitud')))
        modelo.set_problematica(datos_formulario.get('problematica'))

        exito = modelo.actualizar()
        if exito:
            BitacoraService.registrar_accion(
                session=session_data,
                modulo='Solicitudes',
                accion='EDITAR',
                descripcion=f'Solicitud #{id_solicitud} actualizada - re-clasificación IA iniciada'
            )
            tipo_solicitante = datos_formulario.get('tipo_solicitante') or _obtener_tipo_solicitante(id_solicitud)
            priorizar_solicitud_async(id_solicitud, tipo_solicitante)
            return {'success': True, 'message': 'Solicitud actualizada. Re-clasificación IA en proceso.'}
        return {'success': False, 'message': 'No se realizaron cambios.'}
    except ValueError as e:
        return {'success': False, 'message': str(e)}
    except Exception as e:
        print(f"[solicitud_controller] Error: {e}")
        return {'success': False, 'message': 'Error interno del servidor.'}


def reclasificar_solicitud_async(id_solicitud):
    datos = SolicitudModel.buscar_por_id(id_solicitud)
    if not datos:
        return {'success': False, 'message': 'Solicitud no encontrada.'}
    tipo_solicitante = datos.get('tipo_solicitud', 'Comunidad')
    priorizar_solicitud_async(id_solicitud, tipo_solicitante)
    BitacoraService.registrar_accion(
        session=session,
        modulo='Solicitudes',
        accion='CLASIFICAR_IA',
        descripcion=f'Re-clasificación IA disparada para solicitud #{id_solicitud}'
    )
    return {'success': True, 'message': f'Re-clasificación de solicitud #{id_solicitud} en proceso.'}


def _obtener_tipo_solicitante(id_solicitud):
    datos = SolicitudModel.buscar_por_id(id_solicitud)
    if datos:
        return datos.get('tipo_solicitud', 'Comunidad')
    return 'Comunidad'
