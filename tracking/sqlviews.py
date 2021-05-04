from django.db import connections,connection

from .dbutils import executeDDL

drop_tracking_history_view_sql = "DROP VIEW IF EXISTS tracking_history_view; "
create_tracking_history_view_sql = """
CREATE OR REPLACE VIEW tracking_history_view 
AS
SELECT lp.point AS wkb_geometry,
    lp.seen,
    td.registration,
    lp.altitude,
    lp.heading,
    lp.velocity,
    td.symbol,
    td.rin_display,
    td.current_driver,
    td.callsign,
    td.callsign_display,
    td.usual_driver,
    td.usual_location,
    td.contractor_details,
    td.deviceid,
    replace(lower(td.symbol::text), ' '::text, '_'::text) AS symbolid,
    date_part('day'::text, now() - lp.seen) * 24::double precision + date_part('hour'::text, now() - lp.seen) + 1::double precision AS age,
    lp.id,
    td.district,
    td.source_device_type
   FROM tracking_device td
     JOIN tracking_loggedpoint lp ON lp.device_id = td.id
   WHERE td.hidden = false and td.deleted = false
  ORDER BY lp.seen DESC;
"""

drop_tracking_resource_tracking_view_sql = "DROP VIEW IF EXISTS tracking_resource_tracking_view;"
create_tracking_resource_tracking_view_sql = """
CREATE OR REPLACE VIEW tracking_resource_tracking_view
AS
 SELECT resource_tracking_with_age.id,
    resource_tracking_with_age.point,
    resource_tracking_with_age.heading,
    resource_tracking_with_age.velocity,
    resource_tracking_with_age.altitude,
    resource_tracking_with_age.seen,
    resource_tracking_with_age.deviceid,
    resource_tracking_with_age.registration,
    resource_tracking_with_age.rin_display,
    resource_tracking_with_age.current_driver,
    resource_tracking_with_age.callsign,
    resource_tracking_with_age.callsign_display,
    resource_tracking_with_age.usual_driver,
    resource_tracking_with_age.usual_location,
    resource_tracking_with_age.contractor_details,
    resource_tracking_with_age.symbol,
    resource_tracking_with_age.age,
    replace(lower(resource_tracking_with_age.symbol::text), ' '::text, '_'::text) AS symbolid,
    resource_tracking_with_age.district,
    resource_tracking_with_age.district_display,
    resource_tracking_with_age.source_device_type
   FROM ( SELECT tracking_device.id,
            tracking_device.point,
            tracking_device.heading,
            tracking_device.velocity,
            tracking_device.altitude,
            tracking_device.seen,
            tracking_device.deviceid,
            tracking_device.registration,
            tracking_device.rin_display,
            tracking_device.current_driver,
            tracking_device.callsign,
            tracking_device.callsign_display,
            tracking_device.usual_driver,
            tracking_device.usual_location,
            tracking_device.contractor_details,
            tracking_device.symbol,
            date_part('day'::text, now() - tracking_device.seen) * 24::double precision + date_part('hour'::text, now() - tracking_device.seen) + 1::double precision AS age,
            tracking_device.district,
            tracking_device.district_display,
            tracking_device.source_device_type,
            tracking_device.hidden
           FROM tracking_device
           WHERE tracking_device.hidden = false AND tracking_device.deleted = false) resource_tracking_with_age
  WHERE resource_tracking_with_age.age < 168::double precision;
"""

drop_tracking_resource_tracking_ext_view_sql = "DROP VIEW IF EXISTS tracking_resource_tracking_ext_view;"
create_tracking_resource_tracking_ext_view_sql = """
CREATE OR REPLACE VIEW tracking_resource_tracking_ext_view
AS
SELECT resource_tracking_with_age.id,
    resource_tracking_with_age.point,
    resource_tracking_with_age.heading,
    resource_tracking_with_age.velocity,
    resource_tracking_with_age.seen,
    resource_tracking_with_age.deviceid,
    resource_tracking_with_age.registration,
    resource_tracking_with_age.age,
    replace(lower(resource_tracking_with_age.symbol::text), ' '::text, '_'::text) AS symbolid,
    resource_tracking_with_age.district_display,
    resource_tracking_with_age.callsign_display,
    resource_tracking_with_age.current_driver,
    resource_tracking_with_age.district
   FROM ( SELECT tracking_device.id,
            tracking_device.point,
            tracking_device.heading,
            tracking_device.velocity,
            tracking_device.seen,
            tracking_device.deviceid,
            tracking_device.registration,
            tracking_device.callsign_display,
            tracking_device.symbol,
            date_part('day'::text, now() - tracking_device.seen) * 24::double precision + date_part('hour'::text, now() - tracking_device.seen) + 1::double precision AS age,
            tracking_device.current_driver,
            tracking_device.district,
            tracking_device.district_display,
            tracking_device.internal_only
           FROM tracking_device
          WHERE tracking_device.source_device_type::text <> 'tracplus'::text AND tracking_device.source_device_type::text <> 'dfes'::text AND tracking_device.internal_only = false AND tracking_device.deleted = false) resource_tracking_with_age
  WHERE resource_tracking_with_age.age < 168::double precision;
"""

drop_tracking_resource_tracking_ext_temp_view_sql = "DROP VIEW IF EXISTS tracking_resource_tracking_ext_temp_view;"
create_tracking_resource_tracking_ext_temp_view_sql = """
CREATE OR REPLACE VIEW tracking_resource_tracking_ext_temp_view
AS
SELECT resource_tracking_with_age.id,
    resource_tracking_with_age.point,
    resource_tracking_with_age.heading,
    resource_tracking_with_age.velocity,
    resource_tracking_with_age.seen,
    resource_tracking_with_age.deviceid,
    resource_tracking_with_age.registration,
    resource_tracking_with_age.age,
    replace(lower(resource_tracking_with_age.symbol::text), ' '::text, '_'::text) AS symbolid,
    resource_tracking_with_age.district_display,
    resource_tracking_with_age.callsign_display,
    resource_tracking_with_age.current_driver,
    resource_tracking_with_age.district
   FROM ( SELECT tracking_device.id,
            tracking_device.point,
            tracking_device.heading,
            tracking_device.velocity,
            tracking_device.seen,
            tracking_device.deviceid,
            tracking_device.registration,
            tracking_device.callsign_display,
            tracking_device.symbol,
            date_part('day'::text, now() - tracking_device.seen) * 24::double precision + date_part('hour'::text, now() - tracking_device.seen) + 1::double precision AS age,
            tracking_device.current_driver,
            tracking_device.district,
            tracking_device.district_display,
            tracking_device.internal_only
           FROM tracking_device
          WHERE tracking_device.source_device_type::text <> 'tracplus'::text AND tracking_device.deleted = false) resource_tracking_with_age
  WHERE resource_tracking_with_age.age < 168::double precision AND (resource_tracking_with_age.symbol::text = ANY (ARRAY['gang truck'::character varying::text, 'heavy duty'::character varying::text, 'rotary aircraft'::character varying::text, 'fixed wing aircraft'::character varying::text, 'resuce helicopter'::character varying::text, 'helitac'::character varying::text, 'spotter aircraft'::character varying::text, 'aviation fuel truck'::character varying::text, 'float'::character varying::text, 'tender'::character varying::text, 'dozer'::character varying::text, 'grader'::character varying::text, 'loader'::character varying::text, 'waterbomber'::character varying::text, 'snorkel'::character varying::text, 'spotter aircraft'::character varying::text, 'comms bus'::character varying::text]));
"""


def drop_tracking_history_view(log=True):
    executeDDL(connection,drop_tracking_history_view_sql,log=log)

def create_tracking_history_view(log=True):
    executeDDL(connection,create_tracking_history_view_sql,log=log)

def drop_tracking_resource_tracking_view(log=True):
    executeDDL(connection,drop_tracking_resource_tracking_view_sql,log=log)

def create_tracking_resource_tracking_view(log=True):
    executeDDL(connection,create_tracking_resource_tracking_view_sql,log=log)

def drop_tracking_resource_tracking_ext_view(log=True):
    executeDDL(connection,drop_tracking_resource_tracking_ext_view_sql,log=log)

def create_tracking_resource_tracking_ext_view(log=True):
    executeDDL(connection,create_tracking_resource_tracking_ext_view_sql,log=log)

def drop_tracking_resource_tracking_ext_temp_view(log=True):
    executeDDL(connection,drop_tracking_resource_tracking_ext_temp_view_sql,log=log)

def create_tracking_resource_tracking_ext_temp_view(log=True):
    executeDDL(connection,create_tracking_resource_tracking_ext_temp_view_sql,log=log)

def create_all_views(log=True):
    create_tracking_history_view(log=log)
    create_tracking_resource_tracking_view(log=log)
    create_tracking_resource_tracking_ext_view(log=log)
    create_tracking_resource_tracking_ext_temp_view(log=log)


def drop_all_views(log=True):
    drop_tracking_history_view(log=log)
    drop_tracking_resource_tracking_view(log=log)
    drop_tracking_resource_tracking_ext_view(log=log)
    drop_tracking_resource_tracking_ext_temp_view(log=log)

