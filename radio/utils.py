import os
import csv
from decimal import Decimal
from datetime import datetime,date
from colour import Color

from django.contrib.gis.geos import Point
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.template import engines
from django.conf import settings
from django.db import connection

from .models import District,Repeater,get_user_program


def load_repeater(filename,options={}):
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext == ".csv":
        options["model"] = Repeater
        if "set_object" not in options:
            options["set_object"] = set_repeater_from_csv

        _load_csv(filename,options)
    else:
        raise Exception("{} file Not Supported".format(file_ext))

def _is_empty_row(row):
    if row:
        for column in row:
            if column:
                return False
    return True

def _is_new_object(primary_keys,row):
    for column,index in primary_keys:
        if row[index]:
            return True
    return False

def _load_csv(csvfile,options={}):
    #set other options to default value if not configured
    #primary key should be a tuple(column_name,0 based column index), or a list of tuple (column_name,0 based column index)
    if "primary_key" in options and options["primary_key"]:
        if isinstance(options["primary_key"],(list,tuple)):
            if isinstance(options["primary_key"][0],(list,tuple)):
                options["primary_key"] = [(key[0],int(key[1])) for key in options["primary_key"]]
            elif len(options["primary_key"]) == 2:
                options["primary_key"] = [(options["primary_key"][0],int(options["primary_key"][1]))]
            else:
                raise Exception("primary key should be a tuple(column_name,0 based column index), or a list of tuple (column_name,0 based column index)")
        else:
            raise Exception("primary key should be a tuple(column_name,0 based column index), or a list of tuple (column_name,0 based column index)")

        keys = [key for key in options["primary_key"] if key[1] < 0]
        if keys:
            raise Exception("Column index should be 0 based.{}".format(keys))

        keys = [key for key in options["primary_key"] if not options['model']._meta.get_field(key[0])]
        if keys:
            raise Exception("Primary key doesn't exist.{}".format(keys))

    else:
        raise Exception("Missing option 'primary_key'")

    if "is_empty_row" not in options:
        options["is_empty_row"] = _is_empty_row

    #header_rows is the number of header rows not includeing the empty rows
    if "header_rows" not in options:
        options["header_rows"] = 1

    if "is_new_object" not in options:
        options["is_new_object"] = _is_new_object

    #set the fmt parameters to default value if not configured 
    if "fmtparams" not in options:
        fmtparams = {}
        options["fmtparams"] = fmtparams
    else:
        fmtparams = options["fmtparams"]
    for k,v in [("delimiter",','),("quotechar",'|')]:
        if k not in fmtparams:
            fmtparams[k] = v

    results = {
        "created_count": 0,
        "modified_count":0,
        "no_change_count":0,
        "faileds":[]
    }
    rows = []

    def _save_obj():
        if not rows:
            return
        try:
            obj = options["model"]()
            options["set_object"](obj,rows)

            for column,index in options["primary_key"]:
                pkeys[column] = getattr(obj,column)
            try:
                db_obj = options["model"].objects.get(**pkeys)
                update_fields = []
                for field in options["model"]._meta.fields:
                    if field.name in ("id","network","creator","created","modifier","modified"):
                        continue
                    if getattr(db_obj,field.name) == getattr(obj,field.name):
                        #field value is same. ignore
                        continue
                    #field'value was changed, set the new value
                    print("{}.{}: {} <> {}".format(db_obj.site_name,field.name,getattr(db_obj,field.name), getattr(obj,field.name)))
                    setattr(db_obj,field.name,getattr(obj,field.name))
                    update_fields.append(field.name)
                if update_fields:
                    for field in ("modifier","modified"):
                        setattr(db_obj,field,getattr(obj,field))
                        update_fields.append(field)
        
                    #some fields were changed
                    db_obj.save(update_fields=update_fields)
                    results["modified_count"] += 1
                else:
                    results["no_change_count"] += 1
            except ObjectDoesNotExist as ex:
                obj.save()
                results["created_count"] += 1
        except Exception as ex:
            results["faileds"].append("Failed to process rows({}).{}".format(rows,str(ex)))
        finally:
            rows.clear()

    with open(csvfile,'r') as f:
        reader = csv.reader(f,**fmtparams)
        pkeys = {}
        header_rows = options["header_rows"]
        for row in reader:
            #remove the leading and tail space ,and convert the value to None if value is empty string
            row = [c.strip() or None for c in row]
            if options["is_empty_row"](row):
                continue
            if header_rows:
                #is header row
                header_rows -= 1
                continue

            if options["is_new_object"](options["primary_key"],row):
                #start a new object
                #save the previous object first, if have one
                _save_obj()
            
            rows.append(row)
        #save the last object
        _save_obj()

    if results["faileds"]:
        print("""
{1} {0}s have been created
{2} {0}s have been updated
{3} {0}s are not changed.
{4} {0}s are failed.
{5}
""".format(options["model"]._meta.verbose_name_plural,results["created_count"],results["modified_count"],results["no_change_count"],len(results["faileds"]),"    \n".join(results["faileds"])))
    else:
        print("""
{1} {0}s have been created
{2} {0}s have been updated
{3} {0}s are not changed.
""".format(options["model"]._meta.verbose_name_plural,results["created_count"],results["modified_count"],results["no_change_count"]))

def set_repeater_from_csv(obj,rows):
    obj.site_name = rows[0][1]
    obj.last_inspected = datetime.strptime(rows[0][2],"%d/%m/%Y").date() if rows[0][2] else None
    obj.sss_display = (rows[0][3] or "").lower() in ("yes")

    sss_description = [row[4] for row in rows if row[4]]
    obj.sss_description = os.linesep.join(sss_description) if sss_description else None

    if rows[0][5]:
        try:
            district = District.objects.get(name__iexact=rows[0][5])
        except:
            district = District(name=rows[0][5])
            district.save()
    else:
        district = None

    obj.district = district

    obj.channel_number = int(rows[0][6]) if rows[0][6] else None
    obj.point = Point(float(rows[0][8]),float(rows[0][7])) if rows[0][7] and rows[0][8] else None
    obj.link_description = rows[0][9]
    obj.link_point = Point(float(rows[0][11]),float(rows[0][10])) if rows[0][10] and rows[0][11] else None

    obj.tx_frequency = Decimal(rows[0][12]) if rows[0][12] else None
    obj.rx_frequency = Decimal(rows[0][13]) if rows[0][13] else None
    obj.ctcss_tx = Decimal(rows[0][14]) if rows[0][14] else None
    obj.ctcss_rx = Decimal(rows[0][15]) if rows[0][15] else None
    obj.nac_tx = rows[0][16]
    obj.nac_rx = rows[0][17]
    obj.tx_antenna_height = float(rows[0][18]) if rows[0][18] else None
    obj.rx_antenna_height = float(rows[0][19]) if rows[0][19] else None
    obj.output_color = rows[0][20]
    obj.output_radius = float(rows[0][21]) if rows[0][21] else None
    obj.output_clutter = float(rows[0][22]) if rows[0][22] else None

    now = timezone.now()
    obj.creator = get_user_program()
    obj.created = now

    obj.modifier = get_user_program()
    obj.modified = now

rainbow = ["#8B00FF","#2E2B5F","#0000FF","#00FF00","#FFFF00","#FF7F00","#FF0000"]
def create_rainbow_sld(colors,max_dn=255,filter_by_dn=False):
    if colors >= max_dn:
        colors = max_dn

    dns_per_color = int(max_dn / colors)
    remain_dns = max_dn % colors
    gradients = []
    dn = 1
    for i in range(0,colors):
        if i < remain_dns:
            gradients.append([(dn,dn + dns_per_color),None])
            dn += dns_per_color + 1
        else:
            gradients.append([(dn,dn + dns_per_color - 1),None])
            dn += dns_per_color

    base_colorlevels = int((colors + 5) / 6)
    remain_colors = (colors + 5) % 6
    colorlevels = [int( (colors + 5) / 6)] * 6
    if remain_colors:
        for i in range(5,5 - remain_colors,-1):
            colorlevels[i] += 1

    rule_index = 0
    for i in range(0,len(rainbow) - 1):
        start_color = Color(rainbow[i])
        end_color = Color(rainbow[i+1])
        ignore_first_color = i > 0
        for c in list(start_color.range_to(end_color,colorlevels[i])):
            if ignore_first_color:
                ignore_first_color = False
            else:
                gradients[rule_index][1] = str(c)
                rule_index += 1

    if filter_by_dn:
        cur = connection.cursor()
        cur.execute("select distinct dn from radio_repeatertxcoverage")
        dns = [d[0] for d in cur.fetchall()]
        dns.sort()
        tmp = []
        g_index = 0
        length = len(gradients)
        for dn in dns:
            while g_index < length:
                if dn < gradients[g_index][0][0]:
                    #can't find the gradient for the dn
                    break
                elif dn <= gradients[g_index][0][1]:
                    if tmp and tmp[-1][0][0] == gradients[g_index][0][0]:
                        #alread added
                        pass
                    else:
                        tmp.append(gradients[g_index])
                    break
                else:
                    g_index += 1
                    continue
        gradients = tmp


    django_engine = engines['django']

    with open(os.path.join(settings.BASE_DIR,"radio/rainbow.sld")) as f:
        template = django_engine.from_string(f.read())
        sld = template.render({"gradients":gradients})


    with open(os.path.join(settings.BASE_DIR,"media/radio/rainbow_{}.sld".format(colors)),"w") as f:
        f.write(sld)





