import sqlite3
from sqlite3 import Connection
from typing import TextIO


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

    return {'usuario', 'actividad', 'cliente', 'cliente_actividad', 'item_caja'}


def clean_up(backup: TextIO, tables: set) -> str:
    """Takes the content of a .sql file and generates the insert instructions of the values that belong to *tables*.

    Returns:
         The filepath of the temporary .sql file that contains the cleaned up.
    """
    dst = "../adjusted_backup.sql"
    with open(dst, 'w') as adjusted_backup:
        for line in backup:
            if line.startswith("INSERT"):  # Insert values in the backup in the corresponding temporary table.
                _, _, table, _, values = line.split(' ', 4)
                table = table.removesuffix("`").removeprefix("`")
                if table in tables:
                    sql_query = f"INSERT INTO {table} VALUES {values}".replace(r"\'", "")
                    adjusted_backup.write(sql_query)
    return dst


def parse(filepath: str):
    """Parses the .sql file in *filepath* so the old database backup can be "loaded" into the current database.

    This parsing is made by creating a temporary in memory database. The old tables are created and populated, and then
    its contents are adjusted and inserted into the existing tables.
    """
    conn = sqlite3.connect(':memory:')
    tables = _create_temp_tables(conn)  # The tables aren't created from the backup file to avoid any problems.

    with open(filepath) as backup:
        filepath = clean_up(backup, tables)
        with open(filepath) as adjusted_backup:
            script = adjusted_backup.read()
            conn.executescript(script)

    for table in tables:
        print(table, conn.execute(f"SELECT count(*) from {table}").fetchone()[0])

    conn.close()

