import os
import sqlite3
from datetime import date
from sqlite3 import Connection

from gym_manager.contact.core import ContactRepo
from gym_manager.core.base import String
from gym_manager.core.persistence import ActivityRepo, ClientRepo, SubscriptionRepo, TransactionRepo, BalanceRepo


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

    db.execute(
        """CREATE TABLE item_texto_caja (
          id int(10) NOT NULL,
          fecha date NOT NULL,
          descripcion varchar(200) NOT NULL,
          entrada float(6,2) DEFAULT '0.00',
          salida float(6,2) DEFAULT '0.00',
          responsable int(10) NOT NULL,
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

    return {'usuario', 'actividad', 'cliente', 'cliente_actividad', 'item_texto_caja', 'pago'}


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
    # (id, name, price, charge_once, description, locked)
    gen = ((raw[0], raw[1], "0", False, raw[2], False) for raw in conn.execute("SELECT a.id, a.descripcion, a.texto "
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
    gen = (raw for raw in conn.execute("select min(p.fecha), p.id_cliente, p.id_actividad "
                                       "from pago p "
                                       "where (p.id_cliente, p.id_actividad) in ("
                                       "    select id_cliente, id_actividad "
                                       "    from cliente_actividad"
                                       ") and p.fecha >= (?) "
                                       "group by p.id_cliente, p.id_actividad", (since,)))
    subscription_repo.add_all(gen)


def _register_subscription_charging(
        conn: Connection, subscription_repo: SubscriptionRepo, transaction_repo: TransactionRepo, since: date, to: date
):
    """This function extracts charges from the old database. If there is at least one charge in a given (month, year),
    then the given monthly subscription is considered charged, no matter the total amount that was charged.
    """
    to = str(to)
    charges = (raw for raw in conn.execute(
        "select p.id_cliente, max(p.fecha), sum(p.importe), p.id_actividad, c.nombre, a.descripcion, u.usuario "
        "from pago p "
        "inner join actividad a on p.id_actividad = a.id "
        "inner join cliente c on p.id_cliente = c.id "
        "inner join usuario u on p.id_usuario = u.id "
        "where p.fecha >= (?) and p.fecha <= (?) and "
        "group by p.id_cliente, p.id_actividad, strftime('%m-%Y', p.fecha)", (since, to)
    ))

    # Balance date is date.min to avoid parsed transactions to be included in the daily balance of the day when the
    # parsing is done.
    sub_charges = ((raw[1], raw[0], raw[3],
                    transaction_repo.add_raw(("Cobro", raw[0], raw[1], raw[2], "Efectivo", raw[6],
                                              f"Cobro por '{raw[5]}' a cliente '{raw[4]}' en app vieja",
                                              date.min if raw[1] != to else None)))
                   for raw in charges)

    subscription_repo.register_raw_charges(sub_charges)


def parse(
        activity_repo: ActivityRepo,
        client_repo: ClientRepo,
        subscription_repo: SubscriptionRepo,
        transaction_repo: TransactionRepo,
        balance_repo: BalanceRepo,
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

    # This balance is created so the transactions parsed are not included in the daily balance of the day when the
    # parsing is done.
    balance_repo.add(date.min, String("Admin"), {})
    _register_subscription_charging(conn, subscription_repo, transaction_repo, since, date.today())

    conn.close()

    os.remove("../adjusted_backup.sql")
