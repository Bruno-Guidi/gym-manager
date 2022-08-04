import os
import sqlite3
from datetime import date
from sqlite3 import Connection

from gym_manager.contact.core import ContactRepo
from gym_manager.core.persistence import ActivityRepo, ClientRepo, SubscriptionRepo, TransactionRepo
from gym_manager.old_app_info import OldChargesRepo


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


def transfer_backup(backup_path: str, conn: Connection):
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


def _parse_date(today: date, age_str: str | None):
    if age_str is None:
        return today
    try:
        return date(today.year - int(age_str), today.month, today.day)
    except ValueError:
        return today


def _insert_clients(conn: Connection, client_repo: ClientRepo, contact_repo: ContactRepo | None = None):
    today = date.today()
    # (id, name, admission, birthday, tel, dir, is_active)
    gen = ((raw[0], raw[1], raw[2], _parse_date(today, raw[3]), True)
           for raw in conn.execute("select c.id, c.nombre, c.fecha_ingreso, c.edad from cliente c"))
    client_repo.add_all(gen)

    if contact_repo is not None:
        # (name, tel1, tel2, dir, desc, client_id)
        gen = (("", raw[1] if raw[1] is not None else "", "", raw[2] if raw[2] is not None else "", "", raw[0])
               for raw in conn.execute("select c.id, c.telefono, c.direccion from cliente c"))
        contact_repo.add_all(gen)


def _insert_subscriptions(conn: Connection, subscription_repo: SubscriptionRepo, since: date):
    gen = (raw for raw in conn.execute("select min(p.fecha), p.id_cliente, a.descripcion "
                                       "from pago p "
                                       "inner join actividad a on a.id = p.id_actividad "
                                       "where (p.id_cliente, p.id_actividad) in ("
                                       "    select id_cliente, id_actividad "
                                       "    from cliente_actividad"
                                       ") and p.fecha >= (?) "
                                       "group by p.id_cliente, p.id_actividad", (since, )))
    subscription_repo.add_all(gen)


def _register_subscription_charging(
        conn: Connection, subscription_repo: SubscriptionRepo, transaction_repo: TransactionRepo, since: date
):
    """This function extracts charges from the old database. If there is at least one charge in a given (month, year),
    then the given monthly subscription is considered charged, no matter the total amount that was charged.
    """
    charges = (raw for raw in conn.execute("select p.id_cliente, p.fecha, p.importe, p.id_usuario, a.descripcion "
                                           "from pago p inner join actividad a on p.id_actividad = a.id "
                                           "where p.fecha >= (?)", (since,)))

    sub_charges = ((raw[1], raw[0], raw[4], transaction_repo.add_raw(("Cobro", raw[0], raw[1], raw[2],
                                                                      "Efectivo", raw[3], "Desc")))
                   for raw in charges)

    subscription_repo.register_raw_charges(sub_charges)


def _extract_charges(conn: Connection, since: date):
    """Sums charges made after *since* for a given (month, year, activity, client). This is used to visualize if a
    client owes money of a monthly subscription.
    """
    charges = (raw for raw in conn.execute(
        "select c.nombre, a.descripcion, strftime('%m', p.fecha), strftime('%Y', p.fecha), sum(p.importe) "
        "from pago p "
        "inner join actividad a on p.id_actividad = a.id "
        "inner join cliente c on p.id_cliente = c.id "
        "where p.fecha >= (?) "
        "group by strftime('%m', p.fecha), strftime('%Y', p.fecha), p.id_cliente, a.descripcion", (since,)))

    OldChargesRepo.add_all(charges)


def minus_n_months(date_: date, n: int) -> date:
    """Subtracts *n* months to *date_*.
    """
    month = date_.month - n
    year = date_.year
    if month < 1:
        year -= 1
        month = 12 + month
    return date(year, month, 1)


def parse(
        activity_repo: ActivityRepo,
        client_repo: ClientRepo,
        subscription_repo: SubscriptionRepo,
        transaction_repo: TransactionRepo,
        since: date,
        backup_path: str,
        contact_repo: ContactRepo | None = None
):
    conn = sqlite3.connect(':memory:')

    tables = _create_temp_tables(conn)  # The tables aren't created from the backup file to avoid any problems.
    backup_path = clean_up(backup_path, tables)
    transfer_backup(backup_path, conn)

    _insert_activities(conn, activity_repo)
    _insert_clients(conn, client_repo, contact_repo)
    _insert_subscriptions(conn, subscription_repo, since)
    _register_subscription_charging(conn, subscription_repo, transaction_repo, since)

    # The following line will extract charges made in the current month and in the previous one.
    OldChargesRepo.create_model()
    _extract_charges(conn, since=minus_n_months(date.today(), n=1))

    conn.close()

    os.remove("../adjusted_backup.sql")
