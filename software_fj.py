#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Software FJ - Sistema Integral de Gestión de Clientes, Servicios y Reservas
===========================================================================

Aplicación orientada a objetos SIN base de datos. Todo se gestiona con
objetos y listas en memoria; los archivos se usan únicamente para el
registro de eventos y errores (logs/software_fj.log).

Conceptos aplicados
-------------------
* Abstracción      : EntidadBase y Servicio son clases abstractas (ABC).
* Herencia         : Cliente, Servicio y Reserva heredan de EntidadBase;
                     ReservaSala, AlquilerEquipo y Asesoria heredan de Servicio.
* Polimorfismo     : calcular_costo_base(), describir() y validar_parametros()
                     se sobrescriben en cada servicio.
* Encapsulación    : atributos privados con propiedades y validaciones.
* Sobrecarga       : calcular_costo() admite varias formas de llamada
                     (Python simula la sobrecarga con parámetros opcionales
                     y despacho por tipo de argumentos).
* Excepciones      : jerarquía personalizada, try/except/else/finally y
                     encadenamiento con "raise ... from ...".
* Logs             : todo error y evento relevante queda en un archivo.

Ejecución:  python software_fj.py
"""

from __future__ import annotations

import logging
import math
import re
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LOGS (único uso de archivos del sistema)
# ---------------------------------------------------------------------------
DIR_LOGS = Path(__file__).resolve().parent / "logs"
DIR_LOGS.mkdir(exist_ok=True)
ARCHIVO_LOG = DIR_LOGS / "software_fj.log"

logger = logging.getLogger("SoftwareFJ")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _fh = logging.FileHandler(ARCHIVO_LOG, mode="w", encoding="utf-8")
    _fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(_fh)


# ---------------------------------------------------------------------------
# 2. EXCEPCIONES PERSONALIZADAS
# ---------------------------------------------------------------------------
class SoftwareFJError(Exception):
    """Excepción base de todo el sistema."""


class ParametroFaltanteError(SoftwareFJError):
    """Falta un parámetro obligatorio."""


class ClienteInvalidoError(SoftwareFJError):
    """Datos de cliente inválidos."""


class ServicioInvalidoError(SoftwareFJError):
    """Parámetros de servicio inválidos."""


class ServicioNoDisponibleError(SoftwareFJError):
    """El servicio solicitado no está disponible."""


class ReservaInvalidaError(SoftwareFJError):
    """Reserva con datos incorrectos o que no pudo procesarse."""


class OperacionNoPermitidaError(SoftwareFJError):
    """Operación no permitida para el estado actual del objeto."""


class CalculoInconsistenteError(SoftwareFJError):
    """Un cálculo de costos produjo un resultado inconsistente."""


# ---------------------------------------------------------------------------
# 3. CLASE ABSTRACTA BASE
# ---------------------------------------------------------------------------
class EntidadBase(ABC):
    """Entidad general del sistema: todo objeto tiene un id y es describible."""

    _contadores: dict = {}

    def __init__(self) -> None:
        self._id = 0  # se asigna en _registrar(), una vez validado el objeto

    def _registrar(self) -> None:
        """Asigna un id consecutivo por tipo, solo si el objeto se creó bien."""
        tipo = self._tipo_id()
        EntidadBase._contadores[tipo] = EntidadBase._contadores.get(tipo, 0) + 1
        self._id = EntidadBase._contadores[tipo]

    def _tipo_id(self) -> str:
        for base in type(self).__mro__:
            if base.__name__ in ("Cliente", "Servicio", "Reserva"):
                return base.__name__
        return type(self).__name__

    @property
    def id(self) -> int:
        return self._id

    @abstractmethod
    def describir(self) -> str:
        """Devuelve una descripción legible de la entidad."""

    def __str__(self) -> str:
        return self.describir()


# ---------------------------------------------------------------------------
# 4. CLIENTE
# ---------------------------------------------------------------------------
class Cliente(EntidadBase):
    """Cliente con datos personales encapsulados y validados."""

    _RE_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")

    def __init__(self, nombre: Optional[str] = None, documento: Optional[str] = None,
                 email: Optional[str] = None, telefono: Optional[str] = None) -> None:
        super().__init__()
        try:
            self.nombre = nombre
            self.documento = documento
            self.email = email
            self.telefono = telefono
        except SoftwareFJError as exc:
            # Encadenamiento: se conserva la causa original.
            raise ClienteInvalidoError(f"No se pudo crear el cliente: {exc}") from exc
        self._registrar()

    # -- propiedades con validación ------------------------------------------
    @property
    def nombre(self) -> str:
        return self.__nombre

    @nombre.setter
    def nombre(self, valor: Optional[str]) -> None:
        if valor is None:
            raise ParametroFaltanteError("El nombre es obligatorio.")
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ClienteInvalidoError("El nombre debe tener al menos 3 caracteres.")
        if any(ch.isdigit() for ch in valor):
            raise ClienteInvalidoError("El nombre no puede contener números.")
        self.__nombre = valor.strip().title()

    @property
    def documento(self) -> str:
        return self.__documento

    @documento.setter
    def documento(self, valor: Optional[str]) -> None:
        if valor is None:
            raise ParametroFaltanteError("El documento es obligatorio.")
        valor = str(valor).strip()
        if not valor.isdigit() or not 5 <= len(valor) <= 12:
            raise ClienteInvalidoError("El documento debe tener entre 5 y 12 dígitos.")
        self.__documento = valor

    @property
    def email(self) -> str:
        return self.__email

    @email.setter
    def email(self, valor: Optional[str]) -> None:
        if valor is None:
            raise ParametroFaltanteError("El email es obligatorio.")
        if not isinstance(valor, str) or not self._RE_EMAIL.match(valor.strip()):
            raise ClienteInvalidoError(f"Email inválido: '{valor}'.")
        self.__email = valor.strip().lower()

    @property
    def telefono(self) -> str:
        return self.__telefono

    @telefono.setter
    def telefono(self, valor: Optional[str]) -> None:
        if valor is None:
            raise ParametroFaltanteError("El teléfono es obligatorio.")
        valor = str(valor).strip()
        if not valor.isdigit() or not 7 <= len(valor) <= 15:
            raise ClienteInvalidoError("El teléfono debe tener entre 7 y 15 dígitos.")
        self.__telefono = valor

    def describir(self) -> str:
        return f"Cliente #{self.id}: {self.nombre} (Doc: {self.documento}, {self.email})"


# ---------------------------------------------------------------------------
# 5. SERVICIOS (clase abstracta + 3 especializados)
# ---------------------------------------------------------------------------
class Servicio(EntidadBase, ABC):
    """Servicio abstracto. Las subclases definen su propio costo y validación."""

    IVA = 0.19  # impuesto por defecto

    def __init__(self, nombre: str, tarifa_base: float) -> None:
        super().__init__()
        if not isinstance(nombre, str) or not nombre.strip():
            raise ServicioInvalidoError("El servicio necesita un nombre.")
        if not isinstance(tarifa_base, (int, float)) or isinstance(tarifa_base, bool) \
                or tarifa_base <= 0:
            raise ServicioInvalidoError("La tarifa base debe ser un número positivo.")
        self._nombre = nombre.strip()
        self._tarifa_base = float(tarifa_base)
        self._disponible = True

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def tarifa_base(self) -> float:
        return self._tarifa_base

    @property
    def disponible(self) -> bool:
        return self._disponible

    @disponible.setter
    def disponible(self, valor: bool) -> None:
        self._disponible = bool(valor)

    # -- métodos abstractos (polimorfismo) -----------------------------------
    @abstractmethod
    def calcular_costo_base(self, duracion: float) -> float:
        """Costo sin impuestos ni descuentos, según el tipo de servicio."""

    @abstractmethod
    def validar_parametros(self, duracion: float) -> None:
        """Lanza ServicioInvalidoError si los parámetros no son válidos."""

    # -- "sobrecarga" de calcular_costo --------------------------------------
    def calcular_costo(self, duracion: float, *args, **kwargs) -> float:
        """
        Variantes de llamada (sobrecarga simulada):
            calcular_costo(h)                       -> costo base + IVA por defecto
            calcular_costo(h, 0.10)                 -> con 10 % de descuento
            calcular_costo(h, 0.10, 0.19)           -> descuento y IVA explícitos
            calcular_costo(h, descuento=.1, impuesto=0) -> por nombre
        """
        descuento = kwargs.pop("descuento", args[0] if len(args) > 0 else 0.0)
        impuesto = kwargs.pop("impuesto", args[1] if len(args) > 1 else self.IVA)
        if kwargs or len(args) > 2:
            raise ServicioInvalidoError("Argumentos no soportados en calcular_costo().")
        if not 0 <= descuento < 1:
            raise CalculoInconsistenteError(
                f"El descuento debe estar entre 0 y 1 (recibido {descuento}).")
        if not 0 <= impuesto <= 1:
            raise CalculoInconsistenteError(
                f"El impuesto debe estar entre 0 y 1 (recibido {impuesto}).")

        self.validar_parametros(duracion)
        base = self.calcular_costo_base(duracion)
        total = base * (1 - descuento) * (1 + impuesto)
        if not math.isfinite(total) or total <= 0:
            raise CalculoInconsistenteError(f"Costo calculado inconsistente: {total}.")
        return round(total, 2)

    def calcular_costo_detallado(self, duracion: float, descuento: float = 0.0,
                                 impuesto: Optional[float] = None) -> dict:
        """Otra variante: devuelve el desglose completo del costo."""
        imp = self.IVA if impuesto is None else impuesto
        total = self.calcular_costo(duracion, descuento, imp)
        base = self.calcular_costo_base(duracion)
        return {"base": round(base, 2), "descuento": descuento,
                "impuesto": imp, "total": total}


class ReservaSala(Servicio):
    """Reserva de salas: se cobra por hora y según capacidad."""

    def __init__(self, nombre: str, tarifa_hora: float, capacidad: int) -> None:
        super().__init__(nombre, tarifa_hora)
        if not isinstance(capacidad, int) or isinstance(capacidad, bool) or capacidad <= 0:
            raise ServicioInvalidoError("La capacidad de la sala debe ser un entero positivo.")
        self._capacidad = capacidad
        self._registrar()

    def validar_parametros(self, duracion: float) -> None:
        if not isinstance(duracion, (int, float)) or not 1 <= duracion <= 12:
            raise ServicioInvalidoError("Una sala se reserva entre 1 y 12 horas.")

    def calcular_costo_base(self, duracion: float) -> float:
        recargo = 1.15 if self._capacidad > 20 else 1.0  # salas grandes +15 %
        return self.tarifa_base * duracion * recargo

    def describir(self) -> str:
        return (f"Sala '{self.nombre}' | capacidad {self._capacidad} personas | "
                f"${self.tarifa_base:,.0f}/hora")


class AlquilerEquipo(Servicio):
    """Alquiler de equipos: se cobra por día, con depósito fijo."""

    DEPOSITO = 50_000

    def __init__(self, nombre: str, tarifa_dia: float, tipo_equipo: str) -> None:
        super().__init__(nombre, tarifa_dia)
        if not isinstance(tipo_equipo, str) or not tipo_equipo.strip():
            raise ServicioInvalidoError("Debe indicarse el tipo de equipo.")
        self._tipo_equipo = tipo_equipo.strip()
        self._registrar()

    def validar_parametros(self, duracion: float) -> None:
        if not isinstance(duracion, int) or isinstance(duracion, bool) or not 1 <= duracion <= 30:
            raise ServicioInvalidoError("El alquiler es por días enteros (1 a 30).")

    def calcular_costo_base(self, duracion: float) -> float:
        return self.tarifa_base * duracion + self.DEPOSITO

    def describir(self) -> str:
        return (f"Equipo '{self.nombre}' ({self._tipo_equipo}) | "
                f"${self.tarifa_base:,.0f}/día + depósito ${self.DEPOSITO:,}")


class Asesoria(Servicio):
    """Asesoría especializada: tarifa por hora según nivel del asesor."""

    NIVELES = {"junior": 1.0, "senior": 1.5, "experto": 2.0}

    def __init__(self, nombre: str, tarifa_hora: float, especialidad: str, nivel: str) -> None:
        super().__init__(nombre, tarifa_hora)
        if not isinstance(especialidad, str) or not especialidad.strip():
            raise ServicioInvalidoError("La asesoría requiere una especialidad.")
        if not isinstance(nivel, str) or nivel.lower() not in self.NIVELES:
            raise ServicioInvalidoError(
                f"Nivel inválido '{nivel}'. Use: {', '.join(self.NIVELES)}.")
        self._especialidad = especialidad.strip()
        self._nivel = nivel.lower()
        self._registrar()

    def validar_parametros(self, duracion: float) -> None:
        if not isinstance(duracion, (int, float)) or not 0.5 <= duracion <= 8:
            raise ServicioInvalidoError("Una asesoría dura entre 0.5 y 8 horas.")

    def calcular_costo_base(self, duracion: float) -> float:
        return self.tarifa_base * self.NIVELES[self._nivel] * duracion

    def describir(self) -> str:
        return (f"Asesoría '{self.nombre}' en {self._especialidad} | nivel {self._nivel} | "
                f"${self.tarifa_base:,.0f}/hora base")


# ---------------------------------------------------------------------------
# 6. RESERVA
# ---------------------------------------------------------------------------
class EstadoReserva(Enum):
    PENDIENTE = "Pendiente"
    CONFIRMADA = "Confirmada"
    CANCELADA = "Cancelada"
    PROCESADA = "Procesada"


class Reserva(EntidadBase):
    """Integra cliente, servicio, duración y estado."""

    def __init__(self, cliente: Optional[Cliente], servicio: Optional[Servicio],
                 duracion: float) -> None:
        super().__init__()
        if not isinstance(cliente, Cliente):
            raise ReservaInvalidaError("La reserva requiere un cliente válido.")
        if not isinstance(servicio, Servicio):
            raise ReservaInvalidaError("La reserva requiere un servicio válido.")
        if not servicio.disponible:
            raise ServicioNoDisponibleError(
                f"El servicio '{servicio.nombre}' no está disponible.")
        try:
            servicio.validar_parametros(duracion)
        except ServicioInvalidoError as exc:
            raise ReservaInvalidaError(f"Duración inválida para '{servicio.nombre}': {exc}") from exc
        self._cliente = cliente
        self._servicio = servicio
        self._duracion = duracion
        self._estado = EstadoReserva.PENDIENTE
        self._costo_final: Optional[float] = None
        self._creada = datetime.now()
        self._registrar()

    @property
    def estado(self) -> EstadoReserva:
        return self._estado

    @property
    def costo_final(self) -> Optional[float]:
        return self._costo_final

    def confirmar(self) -> None:
        if self._estado is not EstadoReserva.PENDIENTE:
            raise OperacionNoPermitidaError(
                f"No se puede confirmar una reserva en estado {self._estado.value}.")
        if not self._servicio.disponible:
            raise ServicioNoDisponibleError(
                f"El servicio '{self._servicio.nombre}' no está disponible.")
        self._estado = EstadoReserva.CONFIRMADA
        logger.info("Reserva #%s confirmada.", self.id)

    def cancelar(self) -> None:
        if self._estado in (EstadoReserva.PROCESADA, EstadoReserva.CANCELADA):
            raise OperacionNoPermitidaError(
                f"No se puede cancelar una reserva {self._estado.value.lower()}.")
        self._estado = EstadoReserva.CANCELADA
        logger.info("Reserva #%s cancelada.", self.id)

    def procesar(self, descuento: float = 0.0) -> float:
        """Calcula el costo final y cierra la reserva (try/except/else/finally)."""
        try:
            if self._estado is not EstadoReserva.CONFIRMADA:
                raise OperacionNoPermitidaError(
                    "Solo se procesan reservas confirmadas "
                    f"(estado actual: {self._estado.value}).")
            costo = self._servicio.calcular_costo(self._duracion, descuento)
        except (CalculoInconsistenteError, ServicioInvalidoError) as exc:
            # Encadenamiento de excepciones: error técnico -> error de negocio
            raise ReservaInvalidaError(
                f"No se pudo procesar la reserva #{self.id}.") from exc
        else:
            self._costo_final = costo
            self._estado = EstadoReserva.PROCESADA
            logger.info("Reserva #%s procesada. Costo final: $%s", self.id, f"{costo:,.2f}")
            return costo
        finally:
            logger.debug("Fin del intento de procesamiento de la reserva #%s.", self.id)

    def describir(self) -> str:
        costo = f" | Total: ${self._costo_final:,.2f}" if self._costo_final else ""
        return (f"Reserva #{self.id} [{self._estado.value}] {self._cliente.nombre} -> "
                f"{self._servicio.nombre} x {self._duracion}{costo}")


# ---------------------------------------------------------------------------
# 7. GESTOR DEL SISTEMA (listas internas, sin base de datos)
# ---------------------------------------------------------------------------
class GestorFJ:
    """Administra las listas de clientes, servicios y reservas."""

    def __init__(self) -> None:
        self._clientes: list[Cliente] = []
        self._servicios: list[Servicio] = []
        self._reservas: list[Reserva] = []

    def _ejecutar(self, etiqueta: str, funcion, *args, **kwargs):
        """Ejecuta una operación; si falla, registra el error y sigue operando."""
        print(f"\n▶ {etiqueta}")
        try:
            resultado = funcion(*args, **kwargs)
        except SoftwareFJError as exc:
            causa = f" | causa: {exc.__cause__}" if exc.__cause__ else ""
            logger.error("%s -> %s: %s%s", etiqueta, type(exc).__name__, exc, causa)
            print(f"   ⚠ Error controlado y registrado en el log -> {type(exc).__name__}: {exc}{causa}")
            return None
        except Exception as exc:  # error inesperado: el sistema no debe caerse
            logger.critical("%s -> ERROR INESPERADO %s: %s", etiqueta, type(exc).__name__, exc)
            print(f"   ⚠ Error inesperado controlado ({type(exc).__name__}): {exc}")
            return None
        else:
            logger.info("%s -> OK", etiqueta)
            print(f"   ✓ {resultado if resultado is not None else 'Operación completada'}")
            return resultado
        finally:
            logger.debug("Operación finalizada: %s", etiqueta)

    # -- operaciones -----------------------------------------------------------
    def registrar_cliente(self, **datos) -> Cliente:
        cliente = Cliente(**datos)
        self._clientes.append(cliente)
        return cliente

    def registrar_servicio(self, clase: type, *args, **kwargs) -> Servicio:
        servicio = clase(*args, **kwargs)
        self._servicios.append(servicio)
        return servicio

    def crear_reserva(self, cliente, servicio, duracion, confirmar: bool = True) -> Reserva:
        reserva = Reserva(cliente, servicio, duracion)
        if confirmar:
            reserva.confirmar()
        self._reservas.append(reserva)
        return reserva

    def resumen(self) -> None:
        print("\n" + "=" * 70)
        print("RESUMEN FINAL DEL SISTEMA")
        print("=" * 70)
        print(f"Clientes registrados : {len(self._clientes)}")
        for c in self._clientes:
            print("  -", c)
        print(f"Servicios creados    : {len(self._servicios)}")
        for s in self._servicios:
            print("  -", s)
        print(f"Reservas             : {len(self._reservas)}")
        for r in self._reservas:
            print("  -", r)
        print(f"\nLog de eventos y errores: {ARCHIVO_LOG}")


# ---------------------------------------------------------------------------
# 8. SIMULACIÓN DE 15 OPERACIONES (válidas e inválidas)
# ---------------------------------------------------------------------------
def simular() -> None:
    g = GestorFJ()
    logger.info("=== Inicio de la simulación de Software FJ ===")

    # --- Clientes ---
    ana = g._ejecutar("1. Registrar cliente válido (Ana)", g.registrar_cliente,
                      nombre="ana gómez", documento="1020304050",
                      email="ana@correo.com", telefono="3001234567")
    luis = g._ejecutar("2. Registrar cliente válido (Luis)", g.registrar_cliente,
                       nombre="Luis Pérez", documento="80123456",
                       email="luis.perez@mail.co", telefono="3109876543")
    g._ejecutar("3. Cliente con email inválido", g.registrar_cliente,
                nombre="Carlos Ruiz", documento="12345678",
                email="carlos-sin-arroba", telefono="3001112233")
    g._ejecutar("4. Cliente con parámetro faltante (sin nombre)", g.registrar_cliente,
                documento="12345678", email="x@y.com", telefono="3001112233")

    # --- Servicios ---
    sala = g._ejecutar("5. Crear sala válida", g.registrar_servicio, ReservaSala,
                       "Sala Innovación", 80_000, 12)
    g._ejecutar("6. Crear sala con capacidad inválida", g.registrar_servicio, ReservaSala,
                "Sala Fantasma", 80_000, -5)
    equipo = g._ejecutar("7. Crear alquiler de equipo válido", g.registrar_servicio,
                         AlquilerEquipo, "Proyector 4K", 40_000, "Audiovisual")
    asesoria = g._ejecutar("8. Crear asesoría válida", g.registrar_servicio, Asesoria,
                           "Arquitectura de Software", 100_000, "Backend", "senior")
    g._ejecutar("9. Crear asesoría con nivel inválido", g.registrar_servicio, Asesoria,
                "Asesoría X", 100_000, "Datos", "maestro")

    # --- Reservas ---
    r1 = g._ejecutar("10. Reserva válida: Ana + sala 3 h", g.crear_reserva, ana, sala, 3)
    if r1:
        g._ejecutar("11. Procesar reserva con 10 % de descuento", r1.procesar, 0.10)
        g._ejecutar("12. Cancelar reserva ya procesada (no permitido)", r1.cancelar)

    g._ejecutar("13. Reserva con duración inválida (0 horas)", g.crear_reserva, luis, sala, 0)
    g._ejecutar("14. Reserva sin cliente", g.crear_reserva, None, sala, 2)

    if equipo:
        equipo.disponible = False
    g._ejecutar("15. Reserva de servicio NO disponible", g.crear_reserva, luis, equipo, 2)
    if equipo:
        equipo.disponible = True

    r2 = g._ejecutar("16. Reserva válida: Luis + asesoría 2.5 h", g.crear_reserva,
                     luis, asesoria, 2.5)
    if r2:
        g._ejecutar("17. Procesar con descuento inconsistente (150 %)", r2.procesar, 1.5)
        g._ejecutar("18. Procesar correctamente sin descuento", r2.procesar)

    r3 = g._ejecutar("19. Reserva de equipo 3 días y cancelación", g.crear_reserva,
                     ana, equipo, 3)
    if r3:
        g._ejecutar("20. Cancelar reserva de equipo", r3.cancelar)

    # --- Sobrecarga de costos ---
    if sala:
        g._ejecutar("21. Costo sala 2 h (solo IVA)", sala.calcular_costo, 2)
        g._ejecutar("22. Costo sala 2 h (5 % dcto, sin IVA)", sala.calcular_costo, 2,
                    descuento=0.05, impuesto=0)
        g._ejecutar("23. Desglose detallado de costo", sala.calcular_costo_detallado, 4, 0.1)

    g.resumen()
    logger.info("=== Fin de la simulación: el sistema permaneció estable ===")


if __name__ == "__main__":
    simular()
