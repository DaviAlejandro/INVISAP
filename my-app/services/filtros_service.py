import re
from typing import List, Tuple, Optional


class FiltrosQueryBuilder:
    _IDENTIFIER = r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*'
    _IDENTIFIER_RE = re.compile(rf'^{_IDENTIFIER}$')
    _COLUMN = rf'(?:\*|{_IDENTIFIER}(?:\s+AS\s+[A-Za-z_][A-Za-z0-9_]*)?)'
    _COLUMN_LIST_RE = re.compile(
        rf'^\s*{_COLUMN}(?:\s*,\s*{_COLUMN})*\s*$',
        re.IGNORECASE,
    )
    _JOIN_RE = re.compile(
        rf'^(?:(?:LEFT|RIGHT|INNER)(?:\s+OUTER)?\s+)?JOIN\s+'
        rf'{_IDENTIFIER}(?:\s+(?:AS\s+)?[A-Za-z_][A-Za-z0-9_]*)?\s+ON\s+'
        rf'{_IDENTIFIER}\s*=\s*{_IDENTIFIER}$',
        re.IGNORECASE,
    )
    _ORDER_BY_RE = re.compile(
        rf'^\s*{_IDENTIFIER}(?:\s+(?:ASC|DESC))?'
        rf'(?:\s*,\s*{_IDENTIFIER}(?:\s+(?:ASC|DESC))?)*\s*$',
        re.IGNORECASE,
    )

    def __init__(self, table: str, alias: str = ''):
        self._validate_identifier(table)
        if alias:
            self._validate_identifier(alias)
        self.table = table
        self.alias = alias
        self.joins: List[str] = []
        self.where: List[str] = []
        self.params: List[object] = []
        self.group_by: Optional[str] = None
        self.order_by: Optional[str] = None

    def add_join(self, sql: str):
        if not self._JOIN_RE.fullmatch(sql):
            raise ValueError("La cláusula JOIN contiene identificadores o sintaxis no permitidos.")
        self.joins.append(sql)

    def add_where(self, column: str, operator: str, value: object):
        if value == '' or value is None:
            return
        self._validate_identifier(column)
        if operator == 'LIKE':
            self.where.append(f"{column} LIKE %s")
            self.params.append(f"%{value}%")
        elif operator == 'DATE_GTE':
            self.where.append(f"DATE({column}) >= %s")
            self.params.append(value)
        elif operator == 'DATE_LTE':
            self.where.append(f"DATE({column}) <= %s")
            self.params.append(value)
        elif operator == 'EQUALS':
            self.where.append(f"{column} = %s")
            self.params.append(value)
        elif operator == 'BETWEEN':
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                raise ValueError("BETWEEN requiere exactamente dos valores.")
            self.where.append(f"{column} BETWEEN %s AND %s")
            self.params.extend(value)
        else:
            raise ValueError("Operador de filtro no permitido.")

    def build_select(self, columns: str) -> str:
        if not self._COLUMN_LIST_RE.fullmatch(columns):
            raise ValueError("La lista de columnas contiene expresiones no permitidas.")
        sql = f"SELECT {columns} FROM {self.table}"
        if self.alias:
            sql = f"SELECT {columns} FROM {self.table} AS {self.alias}"
        for j in self.joins:
            sql += f" {j}"
        if self.where:
            sql += " WHERE " + " AND ".join(self.where)
        if self.group_by:
            self._validate_identifier_list(self.group_by, self._IDENTIFIER_RE)
            sql += f" GROUP BY {self.group_by}"
        if self.order_by:
            self._validate_identifier_list(self.order_by, self._ORDER_BY_RE)
            sql += f" ORDER BY {self.order_by}"
        return sql

    def get_query(self, columns: str) -> Tuple[str, List[object]]:
        return self.build_select(columns), list(self.params)

    @classmethod
    def _validate_identifier(cls, identifier: str):
        if not isinstance(identifier, str) or not cls._IDENTIFIER_RE.fullmatch(identifier):
            raise ValueError("Identificador SQL no permitido.")

    @staticmethod
    def _validate_identifier_list(value: str, pattern):
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise ValueError("La cláusula SQL contiene identificadores no permitidos.")
