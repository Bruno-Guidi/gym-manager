from gym_manager.core.security import SecurityError

MESSAGE: dict[int, str] = {
    SecurityError.NEEDS_RESP: "Esta acción requiere un responsable.",
    SecurityError.INVALID_RESP: "El responsable ingresado no pudo ser identificado.",
    SecurityError.UNREGISTERED_ACTION: "La acción que esta queriendo ejecutar no esta registrada.",
}

ACTIVITY_NAME_CHARS = 20
ACTIVITY_DESCR_CHARS = 50

DATE_FORMAT, DATE_TIME_FORMAT = "%d/%m/%Y", "%d/%m/%Y - %H:%M"

CLIENT_MIN_DNI, CLIENT_MAX_DNI = 0, 100_000_000
CLIENT_NAME_CHARS = 30
CLIENT_TEL_CHARS = 15
CLIENT_DIR_CHARS = 20

RESP_CHARS = 30

ACTION_NAMES = {
    "Inscribir cliente en actividad": "subscribe",
    "Eliminar cliente de actividad": "cancel",
    "Cobrar actividad": "register_subscription_charge",
    "Cerrar caja diaria": "close_balance",
    "Cancelar turno": "cancel_booking",
    "Cobrar turno": "charge_booking",
    "Crear turno": "create_booking",
    "Actualizar stock ítem": "update_item_amount",
    "Cobrar ítem": "register_item_charge",
    "Extraer de caja": "extract"
}
