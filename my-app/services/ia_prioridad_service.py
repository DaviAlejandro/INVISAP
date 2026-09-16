import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime

import requests

from conexion.conexionBD import connectionBD

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
OLLAMA_BIN = os.environ.get("OLLAMA_BIN", r"C:\Users\Eliot\ollama_portable\ollama.exe")
_REQUEST_TIMEOUT = 120
_OLLAMA_MODEL = "llama3.2:1b"

OBRA_VALOR_TEXTO = {3: "Obra Mayor", 1: "Obra Menor"}
GRAVEDAD_VALOR_TEXTO = {3: "Alta", 1: "Baja"}
ZONA_AGRICOLA_VALOR_TEXTO = {3: "Si", 1: "No"}

PESOS_SOLICITANTE = {"comunidad": 3, "institucion": 2, "institución": 2, "particular": 1}
PESOS_GRAVEDAD = {3: 3, 1: 1}
PESOS_TIPO_OBRA = {"Obra Mayor": 3, "Obra Menor": 1}
PESOS_ZONA_AGRICOLA = {3: 3, 1: 1}

SYSTEM_PROMPT = (
    "Eres un clasificador determinista. Analiza la descripción y la ubicación de la obra "
    "y responde EXCLUSIVAMENTE con un JSON válido y compacto con esta estructura exacta: "
    '{"tipo_obra_valor": 3 | 1, "gravedad_valor": 3 | 1, "es_zona_agricola": 3 | 1}. '
    "Reglas obligatorias (sin valores intermedios, sin decimales, sin texto fuera del JSON): "
    "1) tipo_obra_valor: si la descripción menciona puentes, fallas de borde, avenidas "
    "principales, carreteras, drenaje profundo o infraestructura crítica -> 3 (Obra Mayor). "
    "Si describe bacheo, limpieza, aceras, señalización o mantenimiento menor -> 1 (Obra Menor). "
    "2) gravedad_valor: si el riesgo es inminente, colapso o afecta a personas -> 3 (Alta). "
    "Si es mantenimiento preventivo -> 1 (Baja). "
    "3) es_zona_agricola: si municipio, parroquia, sector o ámbito describen zona rural "
    "con producción agrícola, alimentos, finca, potrero, comunidad campesina -> 3. "
    "Si es zona urbana -> 1. "
    "Cada campo es estrictamente 3 o 1. Nunca decimales, nunca otro número."
)


def _generar_prompt_usuario(descripcion, municipio=None, parroquia=None,
                            sector=None, ambito=None,
                            gravedad_nivel=None, color_semaforo=None,
                            tipo_solicitante=None):
    contexto = []
    if municipio:
        contexto.append(f"Municipio: {municipio}.")
    if parroquia:
        contexto.append(f"Parroquia: {parroquia}.")
    if sector:
        contexto.append(f"Sector: {sector}.")
    if ambito:
        contexto.append(f"Ámbito: {ambito}.")
    if gravedad_nivel:
        contexto.append(f"Gravedad registrada: {gravedad_nivel}.")
    if color_semaforo:
        contexto.append(f"Semáforo de la obra: {color_semaforo}.")
    if tipo_solicitante:
        contexto.append(f"Tipo de solicitante: {tipo_solicitante}.")
    contexto_texto = " ".join(contexto)
    return f"Descripción de la obra: \"{descripcion}\". {contexto_texto}"


def _servidor_disponible():
    try:
        r = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _arrancar_ollama():
    if _servidor_disponible() or not os.path.exists(OLLAMA_BIN):
        return
    try:
        subprocess.Popen(
            [OLLAMA_BIN, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            | getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    except Exception:
        return
    for _ in range(20):
        time.sleep(1)
        if _servidor_disponible():
            return


def _parsear_respuesta(data):
    raw = (data.get("response") or "{}").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {}


def _coercer_entero(valor, permitidos=(3, 1), por_defecto=1):
    """Convierte a int y valida contra el conjunto permitido. Defensa contra respuestas
    mal formadas (decimales, strings, nulos)."""
    try:
        n = int(valor)
    except (TypeError, ValueError):
        try:
            n = int(float(valor))
        except (TypeError, ValueError):
            return por_defecto
    return n if n in permitidos else por_defecto


def _validar_resultado(resultado):
    tipo_valor = _coercer_entero(resultado.get("tipo_obra_valor"), (3, 1), 1)
    grav_valor = _coercer_entero(resultado.get("gravedad_valor"), (3, 1), 1)
    zona_valor = _coercer_entero(resultado.get("es_zona_agricola"), (3, 1), 1)
    return {
        "tipo_obra_valor": tipo_valor,
        "gravedad_valor": grav_valor,
        "es_zona_agricola": zona_valor,
        "tipo_obra": OBRA_VALOR_TEXTO[tipo_valor],
        "gravedad_sugerida": GRAVEDAD_VALOR_TEXTO[grav_valor],
        "zona_agricola": ZONA_AGRICOLA_VALOR_TEXTO[zona_valor],
        "origen": "ia",
        "justificacion": (
            f"IA: tipo_obra_valor={tipo_valor}, "
            f"gravedad_valor={grav_valor}, "
            f"es_zona_agricola={zona_valor}."
        ),
    }


def _clasificar_con_ollama(descripcion, municipio=None, parroquia=None,
                           sector=None, ambito=None,
                           gravedad_nivel=None, color_semaforo=None,
                           tipo_solicitante=None):
    _arrancar_ollama()
    payload = {
        "model": _OLLAMA_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": _generar_prompt_usuario(
            descripcion, municipio, parroquia, sector, ambito,
            gravedad_nivel, color_semaforo, tipo_solicitante,
        ),
        "stream": False,
        "format": "json",
        "options": {"num_predict": 120, "temperature": 0},
    }
    try:
        response = requests.post(
            f"http://{OLLAMA_HOST}/api/generate",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None

    resultado = _parsear_respuesta(data)
    if not resultado:
        return None
    return _validar_resultado(resultado)


def _clasificacion_heuristica(descripcion, municipio=None, parroquia=None,
                              sector=None, ambito=None,
                              gravedad_nivel=None, color_semaforo=None,
                              tipo_solicitante=None):
    desc = (descripcion or "").lower()
    texto_ubicacion = " ".join([
        (municipio or "").lower(),
        (parroquia or "").lower(),
        (sector or "").lower(),
        (ambito or "").lower(),
    ])
    color = (color_semaforo or "").lower()
    gravedad = (gravedad_nivel or "").lower()

    obra_mayor_keywords = [
        "colapso", "colapsar", "falla de borde", "borde", "puente", "viaducto",
        "avenida principal", "reconstrucción", "reconstruir", "carretera",
        "drenaje profundo", "colector pluvial", "infraestructura crítica",
        "maquinaria pesada", "excavadora", "asfaltado",
    ]
    obra_menor_keywords = [
        "bacheo", "bache", "limpieza", "acera", "aceras", "señalización",
        "pintura", "barrido", "desmalezamiento", "luminaria",
        "jornada de vacunación", "vacunación",
    ]
    zona_agricola_keywords = [
        "rural", "agro", "agrícola", "agricola", "agrop", "campesina",
        "campesino", "productor", "cosecha", "finca", "potrero", "parcela",
        "comunidad campesina", "producción de alimentos",
    ]

    tipo_valor = 1
    grav_valor = 1
    if any(p in desc for p in obra_mayor_keywords):
        tipo_valor = 3
        grav_valor = 3
    elif any(p in desc for p in obra_menor_keywords):
        tipo_valor = 1
        grav_valor = 1

    if color in ("rojo", "roja") or gravedad in ("alta", "critica", "crítica"):
        grav_valor = 3

    zona_valor = 1
    if any(p in texto_ubicacion for p in zona_agricola_keywords):
        zona_valor = 3

    if tipo_solicitante and tipo_solicitante.lower() in ("comunidad", "institucion", "institución"):
        if tipo_valor == 1 and grav_valor == 3:
            tipo_valor = 3

    return {
        "tipo_obra_valor": tipo_valor,
        "gravedad_valor": grav_valor,
        "es_zona_agricola": zona_valor,
        "tipo_obra": OBRA_VALOR_TEXTO[tipo_valor],
        "gravedad_sugerida": GRAVEDAD_VALOR_TEXTO[grav_valor],
        "zona_agricola": ZONA_AGRICOLA_VALOR_TEXTO[zona_valor],
        "origen": "heuristica",
        "justificacion": (
            f"Heurística: tipo={tipo_valor}, gravedad={grav_valor}, zona_agricola={zona_valor}."
        ),
    }


def clasificar_solicitud_ia(descripcion, municipio=None, parroquia=None,
                            sector=None, ambito=None,
                            gravedad_nivel=None, color_semaforo=None,
                            tipo_solicitante=None):
    resultado = _clasificar_con_ollama(
        descripcion, municipio, parroquia, sector, ambito,
        gravedad_nivel, color_semaforo, tipo_solicitante,
    )
    if resultado is not None:
        return resultado
    return _clasificacion_heuristica(
        descripcion, municipio, parroquia, sector, ambito,
        gravedad_nivel, color_semaforo, tipo_solicitante,
    )


def calcular_puntaje_prioridad(tipo_solicitante, gravedad_valor, tipo_obra,
                               es_zona_agricola_valor):
    """Puntaje ponderado con conversión explícita a int. Defensa contra valores mal
    formateados: cualquier no-entero cae al peso por defecto (1)."""
    solicitante_lower = (tipo_solicitante or "").lower()
    peso_solicitante = int(PESOS_SOLICITANTE.get(solicitante_lower, 1))
    peso_gravedad = int(PESOS_GRAVEDAD.get(int(gravedad_valor), 1))
    peso_tipo_obra = int(PESOS_TIPO_OBRA.get(tipo_obra, 1))
    peso_zona = int(PESOS_ZONA_AGRICOLA.get(int(es_zona_agricola_valor), 1))

    puntaje = (
        peso_solicitante * 0.20
        + peso_gravedad * 0.35
        + peso_tipo_obra * 0.30
        + peso_zona * 0.15
    )
    rango = round((3 - puntaje) / 2, 3)
    return {
        "puntaje_ponderado": round(puntaje, 3),
        "rango_prioridad": round(min(max(rango, 0.0), 1.0), 3),
        "peso_solicitante": peso_solicitante,
        "peso_gravedad": peso_gravedad,
        "peso_tipo_obra": peso_tipo_obra,
        "peso_zona_agricola": peso_zona,
    }


def calcular_prioridad_con_ia(descripcion, municipio=None, parroquia=None,
                              sector=None, ambito=None,
                              gravedad_nivel=None, color_semaforo=None,
                              tipo_solicitante=None):
    resultado = clasificar_solicitud_ia(
        descripcion, municipio, parroquia, sector, ambito,
        gravedad_nivel, color_semaforo, tipo_solicitante,
    )
    calculo = calcular_puntaje_prioridad(
        tipo_solicitante,
        resultado["gravedad_valor"],
        resultado["tipo_obra"],
        resultado["es_zona_agricola"],
    )
    return {
        "prioridad": calculo["rango_prioridad"],
        "justificacion": resultado["justificacion"],
        "tipo_obra": resultado["tipo_obra"],
        "gravedad_sugerida": resultado["gravedad_sugerida"],
        "zona_agricola": resultado["zona_agricola"],
        "tipo_obra_valor": resultado["tipo_obra_valor"],
        "gravedad_valor": resultado["gravedad_valor"],
        "es_zona_agricola": resultado["es_zona_agricola"],
        "origen": resultado.get("origen", "desconocido"),
        "calculo": calculo,
    }


# ============================================
# WORKER EN SEGUNDO PLANO (APScheduler + Threads)
# ============================================

_scheduler = None
_scheduler_lock = threading.Lock()
_worker_active = False


class PrioridadWorkerModel:
    """Modelo del worker — encapsulamiento POO con atributos privados y setters validados por regex."""

    _RE_JUSTIFICACION = re.compile(r'^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s.,;:!?\'"\-]{3,255}$')
    _RE_RESPONSABLE = re.compile(r'^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s]{2,30}$')
    _RE_ID = re.compile(r'^\d+$')

    def __init__(self):
        self.__id_prioridad = None
        self.__solicitud_id = None
        self.__rango_prioridad = 0.0
        self.__justificacion = ""
        self.__responsable = "Sistema"
        self.__estado = 1
        self.__tipo_obra = None
        self.__gravedad_sugerida = None
        self.__origen = "ia"
        self.__semaforo_id = 1

    @property
    def id_prioridad(self):
        return self.__id_prioridad

    @id_prioridad.setter
    def id_prioridad(self, valor):
        if not self._RE_ID.match(str(valor or '')):
            raise ValueError("ID de prioridad debe ser entero válido.")
        self.__id_prioridad = int(valor)

    @property
    def solicitud_id(self):
        return self.__solicitud_id

    @solicitud_id.setter
    def solicitud_id(self, valor):
        if not self._RE_ID.match(str(valor or '')):
            raise ValueError("ID de solicitud debe ser entero válido.")
        self.__solicitud_id = int(valor)

    @property
    def rango_prioridad(self):
        return self.__rango_prioridad

    @rango_prioridad.setter
    def rango_prioridad(self, valor):
        try:
            v = float(valor)
            if not (0.0 <= v <= 1.0):
                raise ValueError("Rango fuera de [0.0, 1.0].")
            self.__rango_prioridad = round(v, 3)
        except (TypeError, ValueError):
            raise ValueError("Prioridad debe ser número entre 0 y 1.")

    @property
    def justificacion(self):
        return self.__justificacion

    @justificacion.setter
    def justificacion(self, valor):
        if not self._RE_JUSTIFICACION.match(str(valor or '')):
            raise ValueError("Justificación inválida (3-255 caracteres alfanuméricos).")
        self.__justificacion = valor

    @property
    def responsable(self):
        return self.__responsable

    @responsable.setter
    def responsable(self, valor):
        if not self._RE_RESPONSABLE.match(str(valor or '')):
            raise ValueError("Responsable inválido (2-30 caracteres).")
        self.__responsable = valor

    @property
    def estado(self):
        return self.__estado

    @estado.setter
    def estado(self, valor):
        self.__estado = 1 if int(valor) else 0

    @property
    def tipo_obra(self):
        return self.__tipo_obra

    @tipo_obra.setter
    def tipo_obra(self, valor):
        if valor not in ("Obra Mayor", "Obra Menor", None):
            raise ValueError("Tipo de obra debe ser 'Obra Mayor' o 'Obra Menor'.")
        self.__tipo_obra = valor

    @property
    def gravedad_sugerida(self):
        return self.__gravedad_sugerida

    @gravedad_sugerida.setter
    def gravedad_sugerida(self, valor):
        if valor not in ("Alta", "Baja", None):
            raise ValueError("Gravedad debe ser 'Alta' o 'Baja'.")
        self.__gravedad_sugerida = valor

    @property
    def origen(self):
        return self.__origen

    @origen.setter
    def origen(self, valor):
        if valor not in ('ia', 'heuristica', 'error', 'manual', None):
            raise ValueError("Origen inválido.")
        self.__origen = valor

    @property
    def semaforo_id(self):
        return self.__semaforo_id

    @semaforo_id.setter
    def semaforo_id(self, valor):
        if not self._RE_ID.match(str(valor or '')):
            raise ValueError("ID de semáforo debe ser entero válido.")
        self.__semaforo_id = int(valor)

    def _obtener_siguiente_id(self, cursor):
        cursor.execute(
            "SELECT COALESCE(MAX(id_gestion_prioridad), 0) + 1 AS siguiente_id FROM prioridad"
        )
        fila = cursor.fetchone()
        return fila[0] if fila else 1

    def _insertar_prioridad(self, conexion, solicitud_id, rango, justificacion,
                               tipo_obra, gravedad_sugerida, origen, responsable,
                               semaforo_id):
        cursor = None
        try:
            cursor = conexion.cursor()
            siguiente_id = self._obtener_siguiente_id(cursor)
            sql = """INSERT INTO prioridad
                     (id_gestion_prioridad, rango_prioridad, tipo_obra, gravedad_sugerida,
                      origen, fecha_asignacion, responsable_ajuste, justificacion_cambio,
                      estado, semaforo_id)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                siguiente_id, rango, tipo_obra, gravedad_sugerida,
                origen, datetime.now(), responsable, justificacion,
                self.__estado, semaforo_id,
            ))
            conexion.commit()
            return siguiente_id
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

    def _actualizar_solicitud_prioridad(self, conexion, solicitud_id, prioridad_id):
        cursor = None
        try:
            cursor = conexion.cursor()
            sql = "UPDATE solicitudes SET prioridad_id_gestion_prioridad=%s WHERE id_solicitudes=%s"
            cursor.execute(sql, (prioridad_id, solicitud_id))
            conexion.commit()
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

    def guardar_prioridad(self, solicitud_id, rango, justificacion, tipo_obra,
                          gravedad_sugerida, origen, responsable):
        """Valida y persiste la prioridad. Llama métodos privados desde validación pública."""
        self.solicitud_id = solicitud_id
        self.rango_prioridad = rango
        self.justificacion = justificacion
        self.tipo_obra = tipo_obra
        self.gravedad_sugerida = gravedad_sugerida
        self.origen = origen
        self.responsable = responsable

        conexion = connectionBD()
        try:
            prioridad_id = self._insertar_prioridad(
                conexion, solicitud_id, rango, justificacion, tipo_obra,
                gravedad_sugerida, origen, responsable, self.__semaforo_id,
            )
            self._actualizar_solicitud_prioridad(conexion, solicitud_id, prioridad_id)
            self.__id_prioridad = prioridad_id
            return prioridad_id
        finally:
            conexion.close()


def _procesar_priorizacion(solicitud_id, tipo_solicitante):
    """Flujo ETL completo para una solicitud (ejecutado en hilo secundario)."""
    modelo = PrioridadWorkerModel()
    conexion = None
    cursor = None
    try:
        conexion = connectionBD()
        if not conexion or not conexion.is_connected():
            raise Exception("No se pudo conectar a la base de datos.")
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            "SELECT s.id_solicitudes AS id, s.problematica AS descripcion, "
            "s.tipo_solicitud, s.municipio, s.parroquia, s.sector, s.ambito, "
            "s.color_semaforo, s.nivel_gravedad "
            "FROM solicitudes s WHERE s.id_solicitudes = %s AND s.estado = 1",
            (solicitud_id,),
        )
        solicitud = cursor.fetchone()
        if not solicitud:
            raise Exception(f"Solicitud #{solicitud_id} no encontrada o ya inactiva.")

        cursor.execute(
            "SELECT id_gravedad, nivel_gravedad FROM gravedad_obra WHERE estado = 1 LIMIT 1"
        )
        cat_gravedad = cursor.fetchone()
        gravedad_id = cat_gravedad.get('id_gravedad') if cat_gravedad else 1

        resultado_ia = clasificar_solicitud_ia(
            solicitud.get('descripcion'),
            solicitud.get('municipio'),
            solicitud.get('parroquia'),
            solicitud.get('sector'),
            solicitud.get('ambito'),
            solicitud.get('nivel_gravedad'),
            solicitud.get('color_semaforo'),
            solicitud.get('tipo_solicitud'),
        )

        calculo = calcular_puntaje_prioridad(
            solicitud.get('tipo_solicitud'),
            resultado_ia.get('gravedad_valor'),
            resultado_ia.get('tipo_obra'),
            resultado_ia.get('es_zona_agricola'),
        )
        rango = calculo['rango_prioridad']

        cursor.execute("SELECT id_semaforo FROM semaforo WHERE id_semaforo = 1")
        semaforo = cursor.fetchone()
        id_semaforo = semaforo.get('id_semaforo', 1) if semaforo else 1

        modelo.guardar_prioridad(
            solicitud_id=solicitud_id,
            rango=rango,
            justificacion=resultado_ia.get('justificacion', 'Clasificación automática por IA'),
            tipo_obra=resultado_ia.get('tipo_obra'),
            gravedad_sugerida=resultado_ia.get('gravedad_sugerida'),
            origen=resultado_ia.get('origen', 'ia'),
            responsable="IA-Batch",
        )
        print(f"[Worker Async] Solicitud #{solicitud_id} priorizada: rango={rango}")

    except Exception as e:
        print(f"[Worker Async] Error priorizando solicitud {solicitud_id}: {e}")
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass


def priorizar_solicitud_async(id_solicitud, tipo_solicitante):
    """Dispara la priorización en un hilo secundario (no bloquea Flask)."""
    thread = threading.Thread(
        target=_procesar_priorizacion,
        args=(id_solicitud, tipo_solicitante),
        daemon=True,
        name=f"prioridad-async-{id_solicitud}",
    )
    thread.start()
    return thread


def _worker_batch_ejecutar():
    """Worker batch: extrae solicitudes no priorizadas y las procesa cada 5 min."""
    print("[Worker Batch] Iniciando ciclo de procesamiento batch...")
    conexion = None
    cursor = None
    try:
        conexion = connectionBD()
        if not conexion or not conexion.is_connected():
            print("[Worker Batch] No se pudo conectar a BD.")
            return
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT s.id_solicitud, s.tipo_solicitante
            FROM solicitud s
            LEFT JOIN prioridad p ON s.id_solicitud = p.id_prioridad
            WHERE p.id_prioridad IS NULL AND s.estado = 1
        """)
        pendientes = cursor.fetchall()

        if not pendientes:
            print("[Worker Batch] No hay solicitudes pendientes.")
            return

        print(f"[Worker Batch] {len(pendientes)} solicitudes pendientes encontradas.")

        for solicitud in pendientes:
            sid = solicitud.get('id_solicitud')
            t_sol = solicitud.get('tipo_solicitante')
            print(f"[Worker Batch] Disparando priorización async para solicitud #{sid}...")
            try:
                priorizar_solicitud_async(sid, t_sol)
            except Exception as e:
                print(f"[Worker Batch] Error disparando async para {sid}: {e}")
            time.sleep(2)

    except Exception as e:
        print(f"[Worker Batch] Error: {e}")
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass
        print("[Worker Batch] Ciclo completado.")


class _TimerFallback:
    """Fallback simple si APScheduler no está instalado."""

    def __init__(self):
        self._timer = None

    def add_job(self, func, trigger, **kwargs):
        interval = kwargs.get('minutes', 5) * 60
        self._schedule(interval, func)

    def _schedule(self, interval, func):
        def _run():
            try:
                func()
            except Exception as e:
                print(f"[Timer Fallback] Error: {e}")
            self._schedule(interval, func)
        self._timer = threading.Timer(interval, _run)
        self._timer.daemon = True
        self._timer.start()

    def start(self):
        pass

    def shutdown(self):
        if self._timer:
            self._timer.cancel()


def obtener_scheduler():
    global _scheduler
    if _scheduler is None:
        with _scheduler_lock:
            if _scheduler is None:
                try:
                    from apscheduler.schedulers.background import BackgroundScheduler
                    _scheduler = BackgroundScheduler()
                    _scheduler.add_job(
                        _worker_batch_ejecutar,
                        'interval',
                        minutes=5,
                        id='worker_prioridad_batch',
                        replace_existing=True,
                    )
                    print("[Scheduler] APScheduler configurado (intervalo: 5 min).")
                except ImportError:
                    print("[Scheduler] APScheduler no disponible. Usando Timer fallback.")
                    _scheduler = _TimerFallback()
    return _scheduler


def iniciar_scheduler():
    global _worker_active
    scheduler = obtener_scheduler()
    try:
        scheduler.start()
        _worker_active = True
        print("[Scheduler] Scheduler de prioridad iniciado.")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")


def detener_scheduler():
    global _worker_active
    _worker_active = False
    if _scheduler:
        try:
            _scheduler.shutdown()
            print("[Scheduler] Scheduler detenido.")
        except Exception as e:
            print(f"[Scheduler] Error al detener: {e}")
