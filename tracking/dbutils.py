import traceback

def table_exists(cur,schema,table_name,log=False):
    cur.execute("SELECT count(*) FROM pg_catalog.pg_class a join pg_catalog.pg_namespace b on a.relnamespace = b.oid WHERE b.nspname='{}' and a.relname='{}' and a.relkind='r'".format(schema,table_name))
    row = cur.fetchone()
    exists =  False if int(row[0]) == 0 else True
    if log:
        print("The table({}.{}) {} exist".format(schema,table_name,"does" if exists else "doesn't"))
    return exists

def create_table(conn,schema,table_name,create_sql,log=False):
    with conn.cursor() as cur:
        if not table_exists(cur,schema,table_name,log=log):
            #table doesn't exist, create it.
            try:
                cur.execute(create_sql)
                if log :
                    print("Succeed to create the table({}.{}) with sql({})".format(schema,table_name,create_sql))
            except:
                print("Failed to create the table({}.{}) with sql({}).{}".format(schema,table_name,create_sql,traceback.format_exc()))
                if not table_exists(cur,schema,table_name):
                    raise

def execute(conn,sql,log=False):
    with conn.cursor() as cur:
        cur.execute(sql )
        rows = cur.rowcount
        if log:
            print("{1} rows are affected by executing the sql ({0}).".format(sql,rows))
        return rows


def count(conn,schema=None,table=None,sql=None,log=False):
    with conn.cursor() as cur:
        cur.execute(sql if sql else "SELECT count(*) from {}.{}".format(schema,table) )
        rows = int(cur.fetchone()[0])
        if log:
            print("{1} rows are retrieved by sql ({0})".format(sql,rows))

        return rows


