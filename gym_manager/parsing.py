import sqlite3
from datetime import date, timedelta
from sqlite3 import Connection

from gym_manager.core.persistence import ActivityRepo, ClientRepo, SubscriptionRepo, TransactionRepo


def _create_temp_tables(db: Connection):
    """Creates the required tables.
    """
    db.execute(  # Responsible
        """CREATE TABLE usuario (
          id int(10) NOT NULL,
          usuario varchar(60) NOT NULL,
          clave varchar(45) NOT NULL,
          borrado tinyint(1) NOT NULL DEFAULT '0',
          PRIMARY KEY (id)
        )"""
    )

    db.execute(  # Activity
        """CREATE TABLE actividad (
            id int(10),
            descripcion varchar(45) NOT NULL,
            texto text NOT NULL,
            mensual tinyint(1) NOT NULL,
            PRIMARY KEY (`id`)
        )"""
    )

    db.execute(  # Client
        """CREATE TABLE cliente (
            id int(10) NOT NULL,
            nombre varchar(45) NOT NULL,
            direccion varchar(45) DEFAULT NULL,
            telefono varchar(30) DEFAULT NULL,
            fax varchar(30) DEFAULT NULL,
            edad smallint(5) DEFAULT NULL,
            peso smallint(5) DEFAULT NULL,
            altura float(5,2) DEFAULT NULL,
            fecha_ingreso date NOT NULL,
            anotaciones text,
            PRIMARY KEY (id)
        )"""
    )

    db.execute(  # Subscription
        """CREATE TABLE cliente_actividad (
          id_cliente int(10) NOT NULL,
          id_actividad int(10) NOT NULL,
          PRIMARY KEY (id_cliente, id_actividad),
          CONSTRAINT FK_cliente_actividad_1 FOREIGN KEY (id_actividad) REFERENCES actividad (id),
          CONSTRAINT FK_cliente_actividad_2 FOREIGN KEY (id_cliente) REFERENCES cliente (id)
        )"""
    )

    db.execute(  # Transaction
        """CREATE TABLE item_caja (
          id int(10) NOT NULL,
          fecha date NOT NULL,
          codigo int(10) NOT NULL,
          cantidad smallint(5) NOT NULL,
          descripcion varchar(60) NOT NULL,
          precio float(6,2) NOT NULL,
          entrada float(6,2) NOT NULL,
          salida float(6,2) NOT NULL,
          responsable int(10) NOT NULL,
          PRIMARY KEY (id),
          CONSTRAINT FK_item_caja_1 FOREIGN KEY (responsable) REFERENCES usuario (id)
        )"""
    )

    db.execute(  # Stock
        """CREATE TABLE articulo (
          id int(10) NOT NULL,
          descripcion varchar(60) NOT NULL,
          precio float(6,2) NOT NULL,
          PRIMARY KEY (id)
        )"""
    )

    db.execute(  # Transactions that involve activities
        """CREATE TABLE pago (
          fecha date NOT NULL,
          id_cliente int(10) NOT NULL,
          id_actividad int(10) NOT NULL,
          importe float(6,2) NOT NULL,
          fecha_cobro date NOT NULL,
          id_usuario int(10) NOT NULL,
          PRIMARY KEY (fecha,id_cliente,id_actividad),
          CONSTRAINT FK_pago_1 FOREIGN KEY (id_cliente, id_actividad) REFERENCES cliente_actividad (id_cliente, 
          id_actividad),
          CONSTRAINT FK_pago_2 FOREIGN KEY (id_usuario) REFERENCES usuario (id)
        )"""
    )

    db.execute(  # Bookings
        """CREATE TABLE turno (
          id int(10) NOT NULL,
          fecha date NOT NULL,
          nombre varchar(60) NOT NULL,
          horario_inicio tinyint(3) NOT NULL,
          medias_horas tinyint(3) NOT NULL,
          cancha tinyint(3) NOT NULL,
          responsable int(10) DEFAULT NULL,
          importe float(6,2) DEFAULT '0.00',
          fijo tinyint(1) NOT NULL DEFAULT '0',
          borrado tinyint(1) NOT NULL DEFAULT '0',
          fecha_borrado date DEFAULT NULL,
          PRIMARY KEY (id),
          CONSTRAINT FK_turno_1 FOREIGN KEY (responsable) REFERENCES usuario (id)
        )"""
    )

    return {'usuario', 'actividad', 'cliente', 'cliente_actividad', 'item_caja', 'articulo', 'pago', 'turno'}


def clean_up(backup_path: str, tables: set) -> str:
    """Takes the content of a .sql file and generates the insert instructions of the values that belong to *tables*.

    Returns:
         The filepath of the temporary .sql file that contains the cleaned up.
    """
    dst = "../adjusted_backup.sql"
    with open(backup_path) as backup:
        with open(dst, 'w') as cleaned_up_backup:
            for line in backup:
                if line.startswith("INSERT"):  # Insert values in the backup in the corresponding temporary table.
                    _, _, table, _, values = line.split(' ', 4)
                    table = table.removesuffix("`").removeprefix("`")
                    if table in tables:
                        sql_query = f"INSERT INTO {table} VALUES {values}".replace(r"\'", "")
                        cleaned_up_backup.write(sql_query)
    return dst


def transfer_backup(backup_path: str, conn: Connection, tables: set[str]):
    """Parses the .sql file in *filepath* so the old database backup can be "loaded" into the current database.

    This parsing is made by creating a temporary in memory database. The old tables are created and populated, and then
    its contents are adjusted and inserted into the existing tables.
    """
    with open(backup_path) as adjusted_backup:
        script = adjusted_backup.read()
        conn.executescript(script)


def _insert_activities(conn: Connection, activity_repo: ActivityRepo):
    # (name, price, charge_once, description, locked)
    gen = ((raw[0], "0", False, raw[1], False) for raw in conn.execute("SELECT a.descripcion, a.texto "
                                                                       "FROM actividad a"))
    activity_repo.add_all(gen)


def _insert_clients(conn: Connection, client_repo: ClientRepo):
    today = date.today()
    # (id, name, admission, birthday, tel, dir, is_active)
    gen = ((raw[0], raw[1], raw[2], today if raw[3] == 0 or raw[3] is None else today - timedelta(raw[3]),
            raw[4] if raw[4] is not None else "", raw[5] if raw[5] is not None else "", True)
           for raw in conn.execute("select c.id, c.nombre, c.fecha_ingreso, c.edad, c.telefono, c.direccion "
                                   "from cliente c"))
    client_repo.add_all(gen)


def _insert_subscriptions(conn: Connection, subscription_repo: SubscriptionRepo):
    today = date.today()
    gen = ((today, *raw) for raw in conn.execute("select ca.id_cliente, a.descripcion "
                                                 "from cliente_actividad ca "
                                                 "inner join actividad a on ca.id_actividad = a.id"))
    subscription_repo.add_all(gen)


def _register_subscription_charging(
        conn: Connection, subscription_repo: SubscriptionRepo, transaction_repo: TransactionRepo, since: date
):
    charges = (raw for raw in conn.execute("select p.id_cliente, p.fecha_cobro, p.importe, p.id_usuario, a.descripcion "
                                           "from pago p inner join actividad a on p.id_actividad = a.id "
                                           "where p.fecha_cobro >= (?)", (since,)))

    sub_charges = ((raw[0], raw[4], raw[2], transaction_repo.add_raw(("Cobro", raw[0], raw[1], raw[2], "Efectivo",
                                                                      raw[3], "Desc")))
                   for raw in charges)

    subscription_repo.register_raw_charges(sub_charges)


def _register_stock_charging(conn: Connection, transaction_repo: TransactionRepo, since: date):
    """type=raw[0], client=raw[1], when=raw[2], amount=raw[3], method=raw[4],
                                       responsible=raw[5], description=raw[6]
                                       id int(10) NOT NULL,
          fecha date NOT NULL,
          codigo int(10) NOT NULL,
          cantidad smallint(5) NOT NULL,
          descripcion varchar(60) NOT NULL,
          precio float(6,2) NOT NULL,
          entrada float(6,2) NOT NULL,
          salida float(6,2) NOT NULL,
          responsable int(10) NOT NULL,
    """
    query = conn.execute("select ic.fecha, ic.entrada, ic.responsable, ic.cantidad, ic.descripcion, ic.precio "
                         "from item_caja ic where ic.fecha >= (?)", (since,))
    # (type, client, when, amount, method, responsible, description)
    gen = (("Cobro", None, raw[0], raw[1], "Efectivo", raw[2], f"Cobro {raw[3]} '{raw[4]}' a ${raw[5]}")
           for raw in query)
    transaction_repo.add_all(gen)


def parse(
        activity_repo: ActivityRepo,
        client_repo: ClientRepo,
        subscription_repo: SubscriptionRepo,
        transaction_repo: TransactionRepo,
        since: date,
        backup_path: str
):
    conn = sqlite3.connect(':memory:')

    tables = _create_temp_tables(conn)  # The tables aren't created from the backup file to avoid any problems.
    backup_path = clean_up(backup_path, tables)
    transfer_backup(backup_path, conn, tables)

    _insert_activities(conn, activity_repo)
    _insert_clients(conn, client_repo)
    # ToDo register subs after registering its charging. If there is no charging for that sub, remove it.
    _insert_subscriptions(conn, subscription_repo)
    _register_subscription_charging(conn, subscription_repo, transaction_repo, since)
    _register_stock_charging(conn, transaction_repo, since)
    # Load booking info.
    # Generate daily balances.


    conn.close()
