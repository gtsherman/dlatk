from ..mysqlmethods import mysqlMethods as mm
from ..sqlitemethods import sqliteMethods as sm
from .. import dlaConstants as dlac


class DataEngine(object):
	"""
	Class for connecting with the database engine (based on the type of data engine being used) and executing querie.s

	Parameters
	-------------
	corpdb: str
		Corpus Database name.
	sql_host: str
		Host that the mysql server runs on.
	encoding: str
		MySQL encoding
	db_type: str
		Type of the database being used (mysql, sqlite).
	
	"""
	def __init__(self, corpdb=dlac.DEF_CORPDB, sql_host=dlac.MYSQL_HOST, encoding=dlac.DEF_ENCODING,use_unicode=dlac.DEF_UNICODE_SWITCH, db_type=dlac.DB_TYPE):
		self.encoding = encoding
		self.sql_host = sql_host
		self.corpdb = corpdb
		self.use_unicode = use_unicode
		self.db_type = db_type
		self.dataEngine = None

	def connect(self):
		"""
		Establishes connection with the database engine
	
		Returns
		-------------
		Database connection objects
		"""
		if self.db_type == "mysql":
			self.dataEngine = MySqlDataEngine(self.corpdb, self.sql_host, self.encoding)
		if self.db_type == "sqlite":
			self.dataEngine = SqliteDataEngine(self.corpdb)
		dlac.warn("\n%s Data Engine instantiated successfully.\n" % self.db_type)
		return self.dataEngine.get_db_connection()

	def disable_table_keys(self, featureTableName):
		"""
		Disable keys: good before doing a lot of inserts.
		"""
		self.dataEngine.disable_table_keys(featureTableName)

	def enable_table_keys(self, featureTableName):
		"""
		Enables the keys, for use after inserting (and with keys disabled)
		"""
		self.dataEngine.enable_table_keys(featureTableName)

	def execute_get_list(self, usql):
		"""
		Executes the given select query

		Returns
		------------
		Results as list of lists

		"""
		return self.dataEngine.execute_get_list(usql)

	def execute_write_many(self, usql, insert_rows):
		"""
		Executes the given insert query
		
		Parameters
		---------
		usql: string
			Insert statement
		insert_rows: list
			List of rows to insert into table 
		
		"""
		self.dataEngine.execute_write_many(usql, insert_rows)

	def execute(self, sql):
		"""
		Executes a given query
		"""
		self.dataEngine.execute(sql)


class MySqlDataEngine(DataEngine):
	"""
	Class for interacting with the MYSQL database engine.
	Parameters
	------------
	corpdb: str
		Corpus database name.
	mysql_host: str
		Host that the mysql server runs on
	encoding: str
		MYSQL encoding
	"""

	def __init__(self, corpdb, mysql_host, encoding):
		super().__init__()
		(self.dbConn, self.dbCursor, self.dictCursor) = mm.dbConnect(corpdb, host=mysql_host, charset=encoding)

	def get_db_connection(self):
		"""
		Returns
		------------
		Database connection objects
		"""
		return self.dbConn, self.dbCursor, self.dictCursor

	def execute_get_list(self, usql):
		"""
		Executes a given query, returns results as a list of lists
		"""
		return mm.executeGetList(self.corpdb, self.dbCursor, usql, charset=self.encoding, use_unicode=self.use_unicode)

	def disable_table_keys(self, featureTableName):
		"""
		Disable keys: good before doing a lot of inserts.
		"""
		mm.disableTableKeys(self.corpdb, self.dbCursor, featureTableName, charset=self.encoding, use_unicode=self.use_unicode)

	def enable_table_keys(self, featureTableName):
		"""
		Enables the keys, for use after inserting (and with keys disabled)
		"""
		mm.enableTableKeys(self.corpdb, self.dbCursor, featureTableName, charset=self.encoding, use_unicode=self.use_unicode)

	def execute_write_many(self, wsql, insert_rows):
		mm.executeWriteMany(self.corpdb, self.dbCursor, wsql, insert_rows, writeCursor=self.dbConn.cursor(), charset=self.encoding, use_unicode=self.use_unicode)

	def execute(self, sql):
		mm.execute(self.corpdb, self.dbCursor, sql, charset=self.encoding, use_unicode=self.use_unicode)


class SqliteDataEngine(DataEngine):
	# will contain methods similar to MySqlWrapper class
	# these methods will call methods in mysqliteMethods.py (yet to be created) which will be similar to mysqlMethods.py
	def __init__(self, corpdb):
		super().__init__()
		(self.dbConn, self.dbCursor) = sm.dbConnect(corpdb)

	def get_db_connection(self):
		return self.dbConn, self.dbCursor, None

	def enable_table_keys(self, table):
		pass

	def disable_table_keys(self, table):
		pass

	def execute_get_list(self, usql):
		return sm.executeGetList(self.corpdb, self.dbCursor, usql)

	def execute_write_many(self, sql, rows):
		sm.executeWriteMany(self.corpdb, self.dbConn, sql, rows, writeCursor=self.dbConn.cursor())

	def execute(self, sql):
		return sm.execute(self.corpdb, self.dbConn, sql)	
