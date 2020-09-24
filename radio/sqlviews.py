from django.db import connection

def create_repeater_tx_view():
    """
    """
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('''
    DROP VIEW IF EXISTS radio_repeater_tx_v;
    CREATE OR REPLACE VIEW radio_repeater_tx_v AS
    SELECT a.site_name,
    a.last_inspected,
    a.sss_display,
    a.sss_description,
    b.name as district,
    a.channel_number,
    a.point,
    a.link_description,
    ST_AsText(a.link_point) as link_point,
    a.tx_frequency,
    a.ctcss_tx,
    a.nac_tx,
    a.tx_antenna_height,
    a.tx_power,
    a.tx_antenna_gain,
    a.output_color,
    a.output_radius,
    a.output_clutter
    FROM radio_repeater a join radio_district b on a.district_id = b.id
    ''')

def create_repeater_rx_view():
    """
    """
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('''
    DROP VIEW IF EXISTS radio_repeater_rx_v;
    CREATE OR REPLACE VIEW radio_repeater_rx_v AS
    SELECT a.site_name,
    a.last_inspected,
    a.sss_display,
    a.sss_description,
    b.name as district,
    a.channel_number,
    a.point,
    a.link_description,
    ST_AsText(a.link_point) as link_point,
    a.rx_frequency,
    a.ctcss_rx,
    a.nac_rx,
    a.rx_antenna_height,
    a.rx_power,
    a.rx_antenna_gain,
    a.output_color,
    a.output_radius,
    a.output_clutter
    FROM radio_repeater a join radio_district b on a.district_id = b.id
    ''')

def create_all_views():
    create_repeater_tx_view()
    create_repeater_rx_view()
