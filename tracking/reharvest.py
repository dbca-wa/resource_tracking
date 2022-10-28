from datetime import datetime, timedelta
from django.db import models, connection, connections
from django.utils import timezone
from tracking.models import LoggedPoint
from tracking.harvest import save_fleetcare_db, get_fleetcare_creationtime
from data_storage.azure_blob import AzureBlobStorage
from dbca_utils.utils import env
from . import dbutils

delete_before_harvest = 1
overriden = 2
raise_exception = 3

dt_pattern = "%Y-%m-%d %H:%M:%S"


def to_db_timestamp(dt, with_timezone=False):
    if with_timezone:
        return timezone.localtime(dt, timezone=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S+00"
        )
    else:
        return timezone.localtime(dt, timezone=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )


def format_datetime(dt):
    return timezone.localtime(dt).strftime(dt_pattern)


def parse_datetime(dt):
    if not isinstance(dt, datetime):
        dt_str = dt
        try:
            dt = timezone.make_aware(datetime.strptime(dt, dt_pattern))
        except Exception as ex:
            raise Exception(
                "Incorrect datetime string({}), correct datetime pattern should be 'YYYY/MM/DD HH:MM:SS'.{}".format(
                    dt_str, str(ex)
                )
            )
    else:
        dt = timezone.localtime(dt)
    return dt


def import_fleetcare_to_staging_table(
    staging_table, from_datetime, to_datetime, buffer_hours=2
):
    """
    Import fleetcare raw data from blob stroage to staging table
    """
    connection_string = env("FLEETCARE_CONNECTION_STRING")
    if not connection_string:
        raise Exception("Missing fleetcare blob stroage connection string'")

    container_name = env("FLEETCARE_CONTAINER")
    if not container_name:
        raise Exception("Missing fleetcare blob stroage container name")

    if staging_table.lower() == "logentry":
        raise Exception("The staging table for reharvester can't be 'logentry'")

    time_buff = timedelta(hours=buffer_hours)

    from_dt = parse_datetime(from_datetime)
    to_dt = parse_datetime(to_datetime)

    from_dt_source = from_dt - time_buff
    to_dt_source = to_dt + time_buff

    # create the table in staging database
    staging_conn = connections["fleetcare"]
    staging_schema = "public"
    dbutils.create_table(
        staging_conn,
        staging_schema,
        staging_table,
        "CREATE TABLE {}.{} ( like logentry including all)".format(
            staging_schema, staging_table
        ),
    )

    print(
        "Import logpoints which were created between {} and {} from blob storage to staging table {}.buffer = {} hours".format(
            format_datetime(from_dt_source),
            format_datetime(to_dt_source),
            staging_table,
            buffer_hours,
        )
    )

    # clean or check staging table
    rows = dbutils.count(
        staging_conn,
        sql="SELECT count(*) FROM {} WHERE created >= '{}' AND created < '{}'".format(
            staging_table,
            to_db_timestamp(from_dt_source),
            to_db_timestamp(to_dt_source),
        ),
        log=True,
    )
    if rows:
        print(
            "There are {} datas in staging table {} between {} and {}, delete them".format(
                rows,
                staging_table,
                format_datetime(from_dt_source),
                format_datetime(to_dt_source),
            )
        )
        deleted_rows = dbutils.execute(
            staging_conn,
            "DELETE FROM {} WHERE created >= '{}' AND created < '{}'".format(
                staging_table,
                to_db_timestamp(from_dt_source),
                to_db_timestamp(to_dt_source),
            ),
            log=True,
        )
        print(
            "Deleted {} datas from staging table {} between {} and {}".format(
                deleted_rows,
                staging_table,
                format_datetime(from_dt_source),
                format_datetime(to_dt_source),
            )
        )

    # import the data from blob storage to staging database
    storage = AzureBlobStorage(connection_string, container_name)

    oneday = timedelta(days=1)
    day = from_dt_source.date()
    imported_rows = 0
    start = timezone.now()
    while day <= to_dt_source.date():
        day_start = timezone.now()
        metadatas = storage.list_resources(
            "{}/{}/{}/".format(day.year, day.month, day.day)
        )
        metadatas.sort(key=lambda o: o["name"][-24:-5])
        day_rows = 0
        for metadata in metadatas:
            # blob data creation_time is not reliable, extract the timestmap from file name
            creation_time = get_fleetcare_creationtime(metadata["name"])
            if creation_time >= from_dt_source and creation_time < to_dt_source:
                content = storage.get_content(metadata["name"]).decode()
                try:
                    day_rows += dbutils.execute(
                        staging_conn,
                        "INSERT INTO {} (name,created,text) values('{}','{}','{}')".format(
                            staging_table,
                            metadata["name"],
                            to_db_timestamp(creation_time),
                            content,
                        ),
                    )
                except:
                    # Failed to insert the data to staging table.
                    # Check whether the data exists or not, if exists, ignore; otherwise raise exception
                    # the type of the column 'created' of original table 'logentry' is timestamp without timezone, and its value is utc timestamp
                    rows = dbutils.count(
                        staging_conn,
                        sql="SELECT count(*) FROM {}.{} WHERE name='{}' and created='{}' ".format(
                            staging_schema,
                            staging_table,
                            metadata["name"],
                            to_db_timestamp(creation_time),
                        ),
                    )
                    if rows:
                        continue
                    else:
                        raise

        print(
            "{}: Spend {} to import {} rows from blob storage to staging table {}".format(
                day.strftime("%Y/%m/%d"),
                str(timezone.now() - day_start),
                day_rows,
                staging_table,
            )
        )

        imported_rows += day_rows

        day += oneday

    print(
        "Spend {} to import {} rows from blob storage to staging table {} between {} and {}".format(
            str(timezone.now() - start),
            imported_rows,
            staging_table,
            format_datetime(from_dt_source),
            format_datetime(to_dt_source),
        )
    )


def import_fleetcare_from_staging_table(
    model_name,
    staging_table,
    from_datetime,
    to_datetime,
    policy=raise_exception,
    batch=2000,
):
    """
    import fleetcare from staging table
    """
    if staging_table.lower() == "logentry":
        raise Exception("The staging table for reharvester can't be 'logentry'")

    from_dt = parse_datetime(from_datetime)
    to_dt = parse_datetime(to_datetime)

    attrs = {"__module__": "tracking"}
    schema = "public"

    if model_name.lower() == "loggedpoint":
        raise Exception("Must be a model name other than 'LoggedPoint'")
    else:
        attrs = {"__module__": "tracking"}
        schema = "public"
        # create the model
        for f in LoggedPoint._meta.fields:
            attrs[f.name] = f

        loggedpoint_model = type(model_name, (models.Model,), attrs)
        table_name = loggedpoint_model._meta.db_table

        # create the table if not exists before
        dbutils.create_table(
            connection,
            schema,
            table_name,
            "CREATE TABLE {}.{} ( like tracking_loggedpoint including all)".format(
                schema, table_name
            ),
        )

    print(
        "Reharvest logged point between {} and {} from staging table {} to table {}".format(
            from_datetime, to_datetime, staging_table, table_name
        )
    )

    # clean or check reharvest table
    rows = dbutils.count(
        connection,
        sql="SELECT count(*) FROM {} WHERE seen >= '{}' AND seen < '{}'".format(
            table_name, to_db_timestamp(from_dt), to_db_timestamp(to_dt)
        ),
        log=True,
    )
    if rows:
        if policy == delete_before_harvest:
            print(
                "There are {} datas in table {} between {} and {}, delete them".format(
                    rows, table_name, format_datetime(from_dt), format_datetime(to_dt)
                )
            )
            deleted_rows = dbutils.execute(
                connection,
                "DELETE FROM {} WHERE seen >= '{}' AND seen < '{}'".format(
                    table_name, to_db_timestamp(from_dt), to_db_timestamp(to_dt)
                ),
                log=True,
            )
            print(
                "Deleted {} datas from table {} between {} and {}".format(
                    deleted_rows,
                    table_name,
                    format_datetime(from_dt),
                    format_datetime(to_dt),
                )
            )
        elif policy == raise_exception:
            raise Exception(
                "There are {} datas in table {} between {} and {}, delete them before continue".format(
                    rows, table_name, format_datetime(from_dt), format_datetime(to_dt)
                )
            )
        else:
            print(
                "There are {} datas in table {} between {} and {}, will be updated during reharvesting".format(
                    rows, table_name, format_datetime(from_dt), format_datetime(to_dt)
                )
            )

    harvested, created, updated, overriden, errors, suspicious, skipped = (
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    run_times = 0
    start = timezone.now()
    while True:
        (
            harvested1,
            created1,
            updated1,
            overriden1,
            errors1,
            suspicious1,
            skipped1,
        ) = save_fleetcare_db(
            staging_table, loggedpoint_model, from_dt=from_dt, to_dt=to_dt, limit=batch
        )
        if harvested1 == 0:
            break

        harvested += harvested1
        created += created1
        updated += updated1
        overriden += overriden1
        errors += errors1
        suspicious += suspicious1
        skipped += skipped1

        run_times += 1
        print(
            "{}\t: Reharvested {} rows, created {} rows, updated {} rows, overriden {} rows, {} error rows, {} suspicious rows, skipped {} rows".format(
                run_times,
                harvested1,
                created1,
                updated1,
                overriden1,
                errors1,
                suspicious1,
                skipped1,
            )
        )

    print(
        "{}: reharvested {} rows, created {} rows, updated {} rows, overriden {} rows, {} error rows, {} suspicious rows, skipped {} rows".format(
            str(timezone.now() - start),
            harvested,
            created,
            updated,
            overriden,
            errors,
            suspicious,
            skipped,
        )
    )
    return table_name


def reharvest_fleetcare(
    model_name,
    staging_table,
    from_datetime,
    to_datetime,
    policy=raise_exception,
    buffer_hours=2,
    batch=2000,
):
    """
    Reharvest data from blob storage to some table.
    from_datetime: from datatime with pattern "%Y/%m/%d %H:%M:%S" included,
    to_datetime: to datatime with pattern "%Y/%m/%d %H:%M:%S" excluded,
    policy: the way to process the existing data in reharvest table
    """
    start = timezone.now()

    from_dt = parse_datetime(from_datetime)
    to_dt = parse_datetime(to_datetime)

    import_fleetcare_to_staging_table(
        staging_table, from_dt, to_dt, buffer_hours=buffer_hours
    )
    table_name = import_fleetcare_from_staging_table(
        model_name, staging_table, from_dt, to_dt, policy=raise_exception, batch=batch
    )
    print(
        "{0}: reharvest fleetcare data between {3} and {4} from blob storage to loggedpoint table({1}) through staging table({2})".format(
            str(timezone.now() - start),
            table_name,
            staging_table,
            format_datetime(from_dt),
            format_datetime(to_dt),
        )
    )
